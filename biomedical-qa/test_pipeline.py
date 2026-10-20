import unittest
from pipeline import parse_pubmed, parse_trials, parse_fda, prepare, record, retrieve, chunks


class PipelineTests(unittest.TestCase):
    def test_pubmed_preserves_markup_and_all_sections(self):
        rows = parse_pubmed('''<PubmedArticleSet><PubmedArticle><MedlineCitation>
        <PMID>123</PMID><Article><ArticleTitle>Drug <i>X</i> trial</ArticleTitle>
        <Abstract><AbstractText Label="METHODS">No <b>benefit</b>.</AbstractText>
        <AbstractText Label="RESULTS">HER2-positive: 20 mg.</AbstractText></Abstract>
        </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>''')
        self.assertEqual(rows[0]['title'], 'Drug X trial')
        self.assertIn('No benefit.', rows[0]['text'])
        self.assertIn('HER2-positive: 20 mg.', rows[0]['text'])

    def test_current_trial_fields(self):
        rows = parse_trials({'studies': [{'protocolSection': {
            'identificationModule': {'nctId': 'NCT1'},
            'descriptionModule': {'briefSummary': 'Study summary'},
            'conditionsModule': {'conditions': ['Cancer']},
            'armsInterventionsModule': {'interventions': [{'type': 'DRUG', 'name': 'X'}]},
            'statusModule': {'startDateStruct': {'date': '2025-01'}}}}]})
        self.assertEqual(rows[0]['metadata']['conditions'], ['Cancer'])
        self.assertEqual(rows[0]['metadata']['interventions'][0]['name'], 'X')
        self.assertEqual(rows[0]['metadata']['start_date'], '2025-01')

    def test_all_fda_sections_retained(self):
        row = parse_fda({'results': [{'id': 'x', 'indications_and_usage': ['one', 'two']} ]})[0]
        self.assertEqual(row['text'], 'one\ntwo')

    def test_quality_and_negation(self):
        r = record('pubmed', '1', 'Title', 'No benefit at 20 mg in HER2-positive disease.', 'url')
        rows, quality = prepare([r, r, record('pubmed', '2', '', '', 'url')])
        self.assertEqual(len(rows), 1)
        self.assertEqual(quality['duplicates'], 1)
        self.assertEqual(quality['empty_text'], 1)
        self.assertIn('No benefit at 20 mg', rows[0]['text'])

    def test_chunking_does_not_lose_end(self):
        r = record('demo', '1', '', ' '.join(str(i) for i in range(500)), '')
        self.assertTrue(chunks([r])[-1]['passage'].endswith('499'))

    def test_retrieval_and_abstention(self):
        rows = [record('demo', '1', 'Alpha', 'Alpha was studied for cancer.', 'urn:1'),
                record('demo', '2', 'Other', 'Hypertension study.', 'urn:2')]
        self.assertEqual(retrieve(rows, 'Alpha cancer')[0]['id'], '1')
        self.assertEqual(retrieve(rows, 'zzzzqqqq'), [])
        self.assertEqual(retrieve([], 'cancer'), [])
        self.assertEqual(retrieve([record('demo', '3', '', '!!!', 'urn:3')], 'cancer'), [])


if __name__ == '__main__':
    unittest.main()
