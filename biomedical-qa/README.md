# Biomedical literature pipeline: repaired Docker rerun

**To run with Docker, follow [CLOUD_RUN.md](CLOUD_RUN.md).**
The commands below are the optional local workflow; cloud execution uses the
GitHub Actions workflow at the repository's `.github/workflows/biomedical-qa.yml`.

This project replaces the broken execution stages of `big_data_build_a_q_a.ipynb`.
It downloads PubMed abstracts, openFDA label indications, and ClinicalTrials.gov
summaries, preserves their sources, checks data quality, creates word clouds when
text exists, and retrieves relevant passages for a question. It does not train on
invented labels or infer a medical conclusion from a text match.

## 1. Start Docker on Windows

Start Docker Desktop and wait for its Linux engine to report running. Use Linux
containers. In PowerShell, check:

```powershell
docker version
docker compose version
```

`docker version` must show both Client and Server. If the pipe
`dockerDesktopLinuxEngine` is missing, the engine has not started. Check Docker
Desktop's error panel, WSL 2 installation (`wsl --status`), hardware virtualization,
and available disk space. Do not reset Docker or delete its data to fix this error.
Allocate enough memory to Docker; this baseline runs on CPU and needs no CUDA.

## 2. Configure and build

Extract the supplied ZIP, open PowerShell in its `biomedical-qa` folder, then:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose build
```

Set `NCBI_EMAIL` to your contact email. `NCBI_API_KEY` is optional for these small
sequential runs. The old notebook contains a hardcoded key: replace it in your NCBI
account, and remove it from shared copies and repository history as appropriate.
The replacement never includes that key. Keep `.env` private.

The image installs explicit direct dependency versions and runs unit tests during
the build. Transitive dependencies and the base image are not fully locked. For
strict archival reproduction, retain the resulting image, record its digest, and
generate a complete dependency lock after the image is validated on your platform.

## 3. Smoke test without calling external APIs

```powershell
docker compose run --rm pipeline run --demo --out /data/smoke-01
docker compose run --rm pipeline ask --data /data/smoke-01/documents.json --question "Drug Alpha Condition Beta"
```

This uses one clearly marked synthetic fixture. It tests execution and retrieval,
not scientific performance. Use a new output folder on each run.

## 4. Download real data and ask questions

```powershell
docker compose run --rm pipeline run --query "breast cancer" --limit 100 --out /data/breast-cancer-01
docker compose run --rm pipeline ask --data /data/breast-cancer-01/documents.json --question "trastuzumab HER2 breast cancer" --top-k 5 --save /data/breast-cancer-01/answer.json
```

The same disease phrase is used across the three sources. PubMed uses its search
syntax, FDA searches the indications field for a phrase, and trials use a condition
search: source coverage and ordering will differ. Start with 10 records per source,
inspect quality, then raise the limit (maximum 1000 per source in this implementation).
This is a bounded research prototype, not a full corpus big data system.

Results appear in the host `data` folder because Compose mounts it at `/data`.
Each run produces:

- `raw/*.body`: original API response bodies, including error bodies.
- `records.json`: parsed records before quality filtering; warnings and trial
  metadata remain available here.
- `documents.json`: unique source/ID records with nonempty evidence text.
- `quality.json`: counts of usable, duplicate, empty, and missing-ID records.
- `manifest.json`: query, timestamps, per-source status, package versions, and
  code/document hashes. It contains no API key.
- `*-words.png`: word clouds for sources with usable words.
- `answer.json`: retrieved passages, similarity scores, and source links when
  `ask --save` is supplied.

A failed source makes the command exit nonzero even if other sources succeed.
Partial results remain for diagnosis. A source with zero matching records is
recorded as successful with zero records; inspect coverage in `quality.json`.
Repeated reruns should query the saved `documents.json` to keep the evidence fixed.
Re-downloading live data can change results even when the code is identical.

## What was broken in the supplied notebook

Cell numbers below are zero-based positions in its JSON cells array.

- Cell 5 imports `envy`, installs packages inside an import block, and catches
  ImportError without repairing it. An early failure leaves later imports undefined.
  Dependencies now install during the image build and failures stop the build.
- Cells 13–16 lack HTTP status checks/timeouts and use `.text` on XML elements,
  losing inline markup text and all but the first abstract section. The replacement
  checks HTTP responses, retries transient failures, and uses `itertext()` over all
  abstract sections.
- Cell 24 uses old/wrong trial field paths. V2 uses `conditionsModule.conditions`,
  `armsInterventionsModule.interventions` with `type`/`name`, and
  `startDateStruct.date`. Pagination is retained and repeated tokens are rejected.
- Cells 45–47 overwrite all real datasets with dummy sets of integers and random
  binary labels. Those stages are removed. They cannot support valid model training
  or reported accuracy.
- Cells 57–63 assign train-subset Series back into full DataFrames, causing missing
  rows through index alignment. Cell 61 references absent `clean`; cell 64 references
  absent `norm_summary`. The replacement processes complete records directly.
- Stopword removal, digit/punctuation deletion, and stemming damage negation,
  dosage, and biomedical identifiers. Evidence text now retains these features.
- Cells 66/68 call WordCloud on empty text. The replacement checks extracted word
  frequencies before generating an image.
- NLTK resources and spaCy models were downloaded during execution, with missing
  resources possible. The baseline does not need either, or heavyweight unused
  Torch/Transformers/SentenceTransformer imports.
- The notebook title promises Q&A and association mining, but its executable cells
  stop at preprocessing and EDA. The replacement adds transparent lexical passage
  retrieval. It does not silently present entity co-occurrence as a treatment relation.

## How to improve scientific results

First define a test set with domain-reviewed questions, relevant source passages,
drug/disease identifiers, and relation labels. Include negative, uncertain,
contradictory, adverse-event, and no-answer examples. Split by document (and where
appropriate time), keeping related articles out of both training and test sets.
Use Recall@5/10, MRR or nDCG for retrieval, and precision/recall/F1 for entity and
relation extraction. Report results by source and disease, plus confidence intervals.
No performance claim is made until this evaluation exists.

Next compare this TF-IDF baseline with a validated biomedical embedding retriever,
hybrid lexical/vector retrieval, and a reranker on the same held-out questions.
Preserve passage offsets, model revisions, and citations. Add biomedical NER and
entity normalization (for example, drugs to RxNorm and diseases to MeSH) only after
checking licensing, model labels, and domain fit. Classify relations at sentence or
passage level with negation, uncertainty, direction, and evidence type. A clinical
trial studying a drug is not evidence of efficacy; a label and an observational
abstract also carry different meanings.

If a language model is added, require passage citations for every substantive
claim, make it abstain when evidence is insufficient, and test citation accuracy.
Treat retrieved text as untrusted data rather than executable instructions.
Do not select models using training loss or invent labels to create an accuracy score.

For millions of papers, use source-supported bulk downloads, incremental updates,
partitioned Parquet/object storage, persistent metadata, a durable search/vector
index, and an orchestrator with checkpoints and source-specific quotas. A Dockerfile
makes execution portable; it does not by itself distribute ingestion or retrieval.

## Troubleshooting

- HTTP 429/5xx: retries use backoff and Retry-After. Reduce ingestion volume or
  wait, then rerun into a new directory. NCBI requests are spaced conservatively
  below three requests/second. Avoid parallel clients sharing the same quota.
- HTTP 400: check source query syntax and saved raw response; do not retry forever.
- TLS/proxy errors: configure your institution's approved proxy and CA certificates
  in the container. Keep TLS verification enabled.
- Build cannot download packages: check Docker network/proxy settings and available
  disk. The first build needs internet; the synthetic demo needs no API connection
  after the image has been built.
- No useful passages: inspect `quality.json` and the downloaded text, narrow/change
  the disease query, or use question terms appearing in the corpus. A zero score
  returns no match; a positive similarity is not proof that a question was answered.
- Notebook workflow: `rerun_pipeline.ipynb` calls this same pipeline. Its kernel
  requires the packages from `requirements.txt`; it contains no package-install
  magic, credentials, stale outputs, or dummy training stage.

## Official references checked

- NCBI rate limits and API keys: https://support.nlm.nih.gov/kbArticle/?pn=KA-05510
- openFDA endpoint and search syntax: https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/
- ClinicalTrials.gov V2 API: https://clinicaltrials.gov/data-api/api
- Trial study structure: https://clinicaltrials.gov/data-api/about-api/study-data-structure

See `VALIDATION.md` for the actual checks completed on the supplied machine.
