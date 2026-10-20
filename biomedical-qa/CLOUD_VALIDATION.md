# Successful GitHub cloud run — 20 October 2026

The project was added to `Rominaarab/Big-Data` under `biomedical-qa/`. The separate
manual workflow is `.github/workflows/biomedical-qa.yml`. No existing notebook or
pipeline was replaced or deleted.

Verified run: https://github.com/Rominaarab/Big-Data/actions/runs/39374500724

- Workflow: **Biomedical QA (cloud Docker)**, run #1.
- Commit tested: `78809b6b57e477aebc22896eddddeb2e5a2c4e63`.
- GitHub-hosted job completed successfully in 36 seconds.
- Docker image build and build-time unit tests passed.
- Synthetic pipeline execution and source-linked retrieval passed.
- Results were uploaded as a GitHub Actions artifact with seven-day retention.

This supersedes the earlier local Docker limitation in `VALIDATION.md`: cloud
Docker execution is now verified. It does not mean Docker Desktop on the local PC
has been repaired, and local Docker is unnecessary for this workflow.

This run used the explicitly synthetic demo. Live API ingestion was checked
locally as recorded in the earlier report; a live cloud run requires the repository
secret `NCBI_EMAIL` (and optionally a newly generated `NCBI_API_KEY`). Follow
`CLOUD_RUN.md`, disable the demo checkbox, and start with 10 records per source.

The repository also contains `biomedical-qa/biomedical-qa-github.zip`, a sanitized
backup of the prepared project and local validation data. Its validation reports
are snapshots from before this successful cloud run. Code files directly in the
repository, this report, and the linked Actions run are the current references.

## Local cleanup

Future GitHub Actions runs do not depend on any local project files. You may delete
this chat workspace's `outputs/biomedical-qa/`, its `biomedical-qa-*.zip` packages,
and its temporary `work/` folder after retaining any additional local results you
want. The prepared code and archived validation outputs are backed up in GitHub.
Keep unrelated files and original notebooks. No local files were deleted by this
upload. Close Docker Desktop if you do not want its background local resource use.
