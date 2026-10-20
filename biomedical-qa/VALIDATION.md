# Validation on 19 October 2026

## Passed

- Installed all five pinned direct dependencies in an isolated workspace package
  directory. Host execution used Python 3.12.14 on Windows; the Dockerfile targets
  Python 3.11 on Linux, so this does not establish container compatibility.
- Six unit tests passed, including all PubMed abstract sections and inline markup,
  current trial field parsing, all FDA indication sections, data quality filtering,
  negation preservation, complete chunk coverage, lexical retrieval, no-match
  behavior, and punctuation-only text handling.
- The synthetic CLI run completed and retained its explicit synthetic marker.
- Live API smoke tests fetched three nonempty records from each of PubMed, openFDA,
  and ClinicalTrials.gov for `breast cancer`, without reusing the notebook API key.
- A complete CLI acquisition/quality/plot run produced nine usable documents,
  zero duplicate records, zero missing IDs, and zero empty evidence texts. See
  `validation/live-end-to-end/quality.json` and `manifest.json`.
- The `ask` command generated and saved three source-linked passages. A Windows
  console encoding problem with Greek characters was found and fixed; retrieval
  and unit tests were then rerun successfully. The acquisition manifest's code
  hash records the code at acquisition time, before that console-print-only fix.
- `docker compose config --quiet` accepted the Compose configuration.
- The repaired notebook is valid JSON with syntactically valid Python code cells;
  it calls the same pipeline, but was not executed through a Jupyter kernel.

## Not verified / local blockers

- Docker CLI 29.1.3 and Compose v2.40.3 are installed. The Linux engine pipe
  `dockerDesktopLinuxEngine` was unavailable before and after startup attempts.
- A container build attempt also encountered sandbox access denial at the user's
  `.docker/buildx/.lock`. This is an access restriction in this agent session,
  not a demonstrated defect in the Dockerfile or proof of a broken user installation.
- Consequently, no successful image build or container run is claimed. Run the
  README build and smoke-test commands in your regular PowerShell after the Docker
  Linux engine is running. Build-time unit tests will check that image environment.
- This is a small integration smoke test, not exhaustive pagination, outage,
  scale, model-quality, or scientific validation. Similarity scores are not
  confidence probabilities. The sample corpus is far too small to evaluate Q&A
  accuracy; some passages may match only general disease words.
- No supervised drug-disease relation model has been trained. Reviewed labels and
  a held-out evaluation set are needed before such claims can be made.

## Included evidence

`validation/live-api-smoke/` contains the independent endpoint parsing check.
`validation/live-end-to-end/` contains the actual complete CLI run, raw response
bodies, cleaned documents, generated plots, acquisition manifest, and retrieved
passages. These are dated snapshots of public source data and may differ from
future downloads. `validation/demo/` is synthetic and must not be mixed into
scientific analysis.
