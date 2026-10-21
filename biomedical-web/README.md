# Biomedical Evidence Explorer — web application

Cloud-deployable web interface for the existing biomedical-qa research pipeline.
The original notebooks, batch pipeline, and Actions workflow are preserved.

## Features

- Collect live PubMed abstracts, FDA label indications, and trial summaries (up to 25 per source).
- Search the same dataset repeatedly and inspect source-linked evidence passages.
- Filter by source or require an exact term/phrase in a passage or title.
- Display data-quality counts and partial source errors.
- Import Python `documents.json`; export the collection and search results.
- Start immediately with a clearly marked real-data snapshot of nine records.

## Deployment status

The application code and server tests pass, including live API ingestion. It has
not yet been deployed to an active public or private website. The initial Sites
publishing step was blocked by this agent session's command-approval policy. See
VALIDATION.md. A GitHub source URL is not the running website URL.

## Run on a Node/Docker cloud host

Set the service root directory to `biomedical-web`. Runtime: Node 22 or newer.
There are no npm dependencies to install. Start command: `npm start`.
The server binds to `0.0.0.0` and the platform's PORT (default 8080).
Health endpoint: `/api/health`. Alternatively use the supplied Dockerfile.

Checks: `npm test` and `npm run test:server`.

Optional server environment variables: NCBI_EMAIL and NCBI_API_KEY.
Never commit secrets. Small collection requests can run without an API key.
Keep the initial host private: the application has no account system of its own.
A public deployment needs an explicit audience choice and shared API rate limiting.

## Scope and data

This is a JavaScript cloud web adapter, not a Python container running in the
browser. It uses TF-IDF unigrams/bigrams and cosine similarity over 160-word
passages, with 30-word overlap. Unicode tokenization and ties can differ from the
Python baseline. Similarity is not medical confidence and no treatment answer is
generated. It does not claim evaluated drug-disease relation extraction.

Collection state lives in the browser tab. Search/import send records to the
server for processing; no durable research database is configured. Refreshing
returns to the bundled sample, so download snapshots you want to keep. The saved
sample is real public-source data, not a synthetic fixture. Live exports include
raw response bodies and source statuses. Keep private research files out of public
sharing. The service is a bounded prototype, not a high-traffic production system.
