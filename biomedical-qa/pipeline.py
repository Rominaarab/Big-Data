"""Reproducible biomedical evidence retrieval; no fabricated training labels."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import xml.etree.ElementTree as ET


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def xml_text(node):
    return ''.join(node.itertext()).strip() if node is not None else ''


def join_text(values):
    if isinstance(values, str):
        return values.strip()
    return '\n'.join(str(v) for v in (values or []) if v)


def record(source, identifier, title, text, url, **metadata):
    return dict(source=source, id=identifier, title=title or '', text=text or '',
                url=url, metadata=metadata)


def parse_pubmed(body):
    root = ET.fromstring(body)
    error = root.find('.//ERROR')
    if error is not None:
        raise ValueError('PubMed returned an XML error')
    rows = []
    for article in root.findall('.//PubmedArticle'):
        pmid = xml_text(article.find('.//MedlineCitation/PMID'))
        title = xml_text(article.find('.//ArticleTitle'))
        parts = []
        for section in article.findall('.//Abstract/AbstractText'):
            text = xml_text(section)
            if text:
                parts.append((section.get('Label', '') + ': ' if section.get('Label') else '') + text)
        rows.append(record('pubmed', pmid, title, '\n'.join(parts),
                           f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'))
    return rows


def parse_fda(payload):
    rows = []
    for item in payload.get('results', []):
        names = item.get('openfda') or {}
        generic = join_text(names.get('generic_name'))
        brand = join_text(names.get('brand_name'))
        identifier = item.get('id', '')
        rows.append(record('fda', identifier, generic or brand,
                           join_text(item.get('indications_and_usage')),
                           'https://api.fda.gov/drug/label.json?search=id:' + identifier,
                           generic_name=generic, brand_name=brand,
                           warnings=join_text(item.get('warnings')),
                           effective_time=item.get('effective_time', '')))
    return rows


def parse_trials(payload):
    rows = []
    for study in payload.get('studies', []):
        p = study.get('protocolSection') or {}
        identity = p.get('identificationModule') or {}
        status = p.get('statusModule') or {}
        description = p.get('descriptionModule') or {}
        conditions = (p.get('conditionsModule') or {}).get('conditions') or []
        interventions = (p.get('armsInterventionsModule') or {}).get('interventions') or []
        identifier = identity.get('nctId', '')
        rows.append(record('trials', identifier, identity.get('briefTitle', ''),
                           description.get('briefSummary', ''),
                           f'https://clinicaltrials.gov/study/{identifier}',
                           conditions=conditions, interventions=interventions,
                           status=status.get('overallStatus', ''),
                           start_date=(status.get('startDateStruct') or {}).get('date', '')))
    return rows


class Client:
    def __init__(self, raw_dir):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        self.session = requests.Session()
        retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=['GET'], respect_retry_after_header=True)
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        self.session.headers['User-Agent'] = 'biomedical-evidence-pipeline/1.0'
        self.raw_dir = Path(raw_dir)
        self.last_ncbi = 0.0
        self.number = 0

    def get(self, url, params, allow_empty=False):
        if 'ncbi.nlm.nih.gov' in url:
            # Conservative sequential rate even when a key is supplied.
            time.sleep(max(0, .36 - (time.monotonic() - self.last_ncbi)))
            self.last_ncbi = time.monotonic()
        response = self.session.get(url, params=params, timeout=(15, 90))
        self.number += 1
        # Save response bodies only: request URLs may contain credentials.
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / f'{self.number:04d}.body').write_bytes(response.content)
        if allow_empty and response.status_code == 404:
            payload = response.json()
            if payload.get('error', {}).get('code') == 'NOT_FOUND':
                return None
        if response.status_code >= 400:
            raise RuntimeError(f'HTTP {response.status_code} from {url}; response saved to raw/')
        return response


def fetch_pubmed(client, query, limit):
    base = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    auth = {'tool': 'biomedical_evidence_pipeline'}
    for env, field in [('NCBI_API_KEY', 'api_key'), ('NCBI_EMAIL', 'email')]:
        if os.getenv(env):
            auth[field] = os.environ[env]
    result = client.get(base + 'esearch.fcgi', dict(auth, db='pubmed', term=query,
                        retmax=limit, retmode='json', sort='relevance')).json()
    if 'error' in result or 'esearchresult' not in result:
        raise ValueError('Invalid PubMed search response')
    ids = result['esearchresult'].get('idlist', [])
    rows = []
    for start in range(0, len(ids), 100):
        response = client.get(base + 'efetch.fcgi', dict(auth, db='pubmed',
                              id=','.join(ids[start:start + 100]), retmode='xml'))
        rows.extend(parse_pubmed(response.content))
    return rows


def fetch_fda(client, query, limit):
    rows = []
    # Field-scoped search: do not match unrelated mentions elsewhere in labels.
    phrase = query.replace('"', ' ').replace('\\', ' ')
    while len(rows) < limit:
        response = client.get('https://api.fda.gov/drug/label.json',
                              {'search': f'indications_and_usage:"{phrase}"',
                               'limit': min(100, limit - len(rows)), 'skip': len(rows)},
                              allow_empty=True)
        if response is None:
            break
        payload = response.json()
        page = parse_fda(payload)
        rows.extend(page)
        if not page or len(rows) >= payload.get('meta', {}).get('results', {}).get('total', 0):
            break
        time.sleep(.3)
    return rows


def fetch_trials(client, query, limit):
    rows, token, seen = [], None, set()
    while len(rows) < limit:
        params = {'query.cond': query, 'format': 'json', 'pageSize': min(100, limit-len(rows))}
        if token:
            params['pageToken'] = token
        payload = client.get('https://clinicaltrials.gov/api/v2/studies', params).json()
        if 'studies' not in payload:
            raise ValueError('Invalid ClinicalTrials.gov response')
        page = parse_trials(payload)
        rows.extend(page)
        token = payload.get('nextPageToken')
        if not page or not token:
            break
        if token in seen:
            raise ValueError('Repeated trial pagination token')
        seen.add(token)
        time.sleep(.3)
    return rows[:limit]


def prepare(rows):
    clean, seen = [], set()
    quality = {'input_records': len(rows), 'duplicates': 0, 'missing_id': 0,
               'empty_text': 0, 'usable_by_source': {}}
    for row in rows:
        key = (row['source'], row['id'])
        if not row['id']:
            quality['missing_id'] += 1
            continue
        if key in seen:
            quality['duplicates'] += 1
            continue
        seen.add(key)
        if not row['text'].strip():
            quality['empty_text'] += 1
            continue
        # Keep punctuation, case, numbers and negation in biomedical evidence.
        row = dict(row, text=re.sub(r'\s+', ' ', row['text']).strip())
        clean.append(row)
    quality['usable_by_source'] = dict(Counter(r['source'] for r in clean))
    quality['usable_records'] = len(clean)
    return clean, quality


def chunks(rows, size=160, overlap=30):
    result = []
    for row in rows:
        words = row['text'].split()
        for start in range(0, len(words), size-overlap):
            result.append(dict(row, chunk_start_word=start,
                               passage=' '.join(words[start:start+size])))
            if start+size >= len(words):
                break
    return result


def retrieve(rows, question, top_k=5):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    passages = chunks(rows)
    if not passages:
        return []
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True,
                               token_pattern=r'(?u)\b[\w-]+\b')
    try:
        matrix = vectorizer.fit_transform([p['title'] + ' ' + p['passage'] for p in passages])
    except ValueError as exc:
        if 'empty vocabulary' in str(exc):
            return []
        raise
    scores = cosine_similarity(vectorizer.transform([question]), matrix).ravel()
    results = []
    for i in scores.argsort()[::-1]:
        if scores[i] <= 0 or len(results) >= top_k:
            break
        p = passages[int(i)]
        results.append({k: p[k] for k in ['source', 'id', 'title', 'url', 'passage', 'chunk_start_word']})
        results[-1]['retrieval_score'] = round(float(scores[i]), 6)
    return results


def plot_words(rows, destination):
    from wordcloud import WordCloud
    for source in ['pubmed', 'fda', 'trials']:
        text = ' '.join(r['text'] for r in rows if r['source'] == source)
        cloud = WordCloud(width=1200, height=600, background_color='white', random_state=42)
        frequencies = cloud.process_text(text)
        if frequencies:
            cloud.generate_from_frequencies(frequencies).to_file(str(destination / f'{source}-words.png'))


def demo_rows():
    # Explicit synthetic fixtures, never represented as downloaded evidence.
    return [record('demo', 'synthetic-1', 'Synthetic retrieval test',
                   'Drug Alpha was studied for Condition Beta. This synthetic text is not clinical evidence.',
                   'urn:synthetic:1')]


def run(args):
    target = Path(args.out)
    if target.exists() and any(target.iterdir()):
        raise ValueError('Output directory is not empty; choose a new --out to preserve the previous snapshot')
    target.mkdir(parents=True, exist_ok=True)
    if not args.demo and not os.getenv('NCBI_EMAIL'):
        raise ValueError('Set NCBI_EMAIL in .env for live PubMed requests')
    started = datetime.now(timezone.utc).isoformat()
    rows, status = [], {}
    if args.demo:
        rows = demo_rows()
        status['demo'] = 'synthetic smoke test only'
    else:
        client = Client(target / 'raw')
        for name, fetch in [('pubmed', fetch_pubmed), ('fda', fetch_fda), ('trials', fetch_trials)]:
            try:
                batch = fetch(client, args.query, args.limit)
                rows.extend(batch)
                status[name] = {'state': 'ok', 'fetched': len(batch)}
            except Exception as exc:
                # Exception messages from HTTP libraries can contain secret request URLs.
                status[name] = {'state': 'failed', 'error_type': type(exc).__name__}
                print(f'{name} failed ({type(exc).__name__}); inspect raw response bodies.', file=sys.stderr)
    save_json(target / 'records.json', rows)
    clean, quality = prepare(rows)
    save_json(target / 'documents.json', clean)
    save_json(target / 'quality.json', quality)
    versions = {}
    for name in ['requests', 'numpy', 'scikit-learn', 'matplotlib', 'wordcloud']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'not installed'
    save_json(target / 'manifest.json', dict(started_utc=started, query=args.query,
              limit_per_source=args.limit, synthetic=args.demo, source_status=status,
              python=platform.python_version(), packages=versions,
              code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              documents_sha256=hashlib.sha256((target/'documents.json').read_bytes()).hexdigest()))
    if clean:
        plot_words(clean, target)
    failed = any(isinstance(v, dict) and v['state'] == 'failed' for v in status.values())
    print(json.dumps({'output': str(target), 'quality': quality, 'source_status': status}, indent=2))
    if failed or not clean:
        raise RuntimeError('Run incomplete; inspect quality.json and manifest.json before using outputs')


def ask(args):
    path = Path(args.data)
    rows = json.loads(path.read_text(encoding='utf-8'))
    results = retrieve(rows, args.question, args.top_k)
    payload = dict(question=args.question, method='TF-IDF passage retrieval',
                   note='Scores measure text similarity, not clinical confidence. Passages are evidence candidates; no treatment conclusion is inferred.',
                   synthetic=any(r['source'] == 'demo' for r in rows), results=results)
    if args.save:
        if Path(args.save).resolve() == path.resolve():
            raise ValueError('--save must not overwrite the input documents')
        save_json(args.save, payload)
    # JSON escapes keep Windows legacy console encodings from failing on Greek symbols.
    # The saved JSON file above still contains the original Unicode text.
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run_parser = sub.add_parser('run')
    run_parser.add_argument('--query', default='cancer', help='Disease phrase shared across sources')
    run_parser.add_argument('--limit', type=int, default=100, help='Maximum per source (1-1000)')
    run_parser.add_argument('--out', required=True)
    run_parser.add_argument('--demo', action='store_true')
    ask_parser = sub.add_parser('ask')
    ask_parser.add_argument('--data', required=True, help='Path to documents.json')
    ask_parser.add_argument('--question', required=True)
    ask_parser.add_argument('--top-k', type=int, default=5)
    ask_parser.add_argument('--save')
    args = parser.parse_args()
    if args.command == 'run' and (not 1 <= args.limit <= 1000 or not args.query.strip()):
        parser.error('Use a nonempty query and --limit between 1 and 1000')
    if args.command == 'ask' and (not args.question.strip() or not 1 <= args.top_k <= 50):
        parser.error('Use a nonempty question and --top-k between 1 and 50')
    try:
        (run if args.command == 'run' else ask)(args)
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
