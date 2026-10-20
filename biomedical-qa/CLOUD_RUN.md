# Run entirely on GitHub

The repository stores the code. GitHub Actions builds and runs Docker on a temporary
GitHub-hosted Linux machine. Docker Desktop and local data folders are unnecessary
for future runs. Your browser still uses ordinary browser memory; the pipeline
computation and result storage use GitHub resources.

## Repository layout

Keep every existing notebook and pipeline. Add this project under `biomedical-qa/`
and place the workflow at the repository root path
`.github/workflows/biomedical-qa.yml`. The packaged workflow is provided inside
this project's `.github/workflows/` directory for transport; on GitHub it belongs
at the repository root, outside `biomedical-qa/`.

Do not commit `.env`, local Python dependencies, caches, or the original exposed
API key. Existing notebooks are preserved; replace the exposed key in your NCBI
account separately.

## Run from a browser

1. Open the repository's Actions tab.
2. Select **Biomedical QA (cloud Docker)**, then **Run workflow**.
3. Leave **demo** enabled for the first run. The default branch must contain the
   workflow for this manual trigger to appear.
4. Open the run to see logs. After completion, its **Artifacts** section contains
   `biomedical-results-...`, including documents, quality, source statuses, plots,
   and answer JSON. Artifacts expire after seven days in this workflow.

For real API acquisition, open repository **Settings > Secrets and variables >
Actions**, add `NCBI_EMAIL`, and optionally add a newly generated `NCBI_API_KEY`.
Then run again with **demo** disabled. Start with 10 records per source. Inputs
are passed as environment variables and quoted arguments, rather than inserted
directly into shell code. Each run has a fresh output directory on a fresh runner.

The workflow is manual only, has a 20-minute timeout, and requests read-only
repository access. It does not modify or delete existing pipelines. It does not
publish an image registry or start a persistent website. Standard hosted runners
are free for public repositories; storage and private-repository allowances are
subject to your GitHub plan and limits. Check your billing settings before large
or frequent runs.

## Can you delete local files?

After the new files are committed to GitHub and a cloud run succeeds, you can
delete the copies created for this task: the `outputs/biomedical-qa/` folder,
`outputs/biomedical-qa-docker.zip`, and this chat workspace's `work/` folder.
The latter contains temporary Python packages used only for local verification.
Keep any local results you want to retain until they have been backed up: run
artifacts are temporary and do not automatically become permanent repository files.
Do not delete unrelated projects or your original notebook unless you independently
want to remove them. Deleting local files does not delete GitHub commits or stop
GitHub-hosted runs. Local copies consume disk while stored; inactive files do not
use pipeline RAM. Closing Docker Desktop stops its local background resource use.

## Official documentation

- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
- https://docs.github.com/en/actions/how-tos/store-and-share-data
- https://docs.github.com/en/actions/concepts/billing-and-usage
