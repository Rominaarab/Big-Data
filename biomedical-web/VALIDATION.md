# Web adapter validation — 21 October 2026

- Eight Node tests passed: XML text/structured abstracts, API field parsing,
  quality filtering, sample retrieval, required phrase/source filtering, chunk
  coverage, API request validation/origin rejection, client script syntax, and
  partial upstream failure handling.
- A live collection request returned nine usable real records: three each from
  PubMed, openFDA, and ClinicalTrials.gov; all three source statuses were `ok`.
- Worker ESM artifact build and validation were run before packaging.
- The standalone Node server passed HTTP integration checks: health endpoint,
  HTML delivery, and a same-origin search against the real saved snapshot.
- The local preview server started successfully. Browser visual/interaction QA
  could not be completed: the in-app browser could not reach the loopback server.
- A new owner-private Sites project was registered, but no version was saved or
  deployed. Its publishing helper input was rejected by this session's approval
  policy. The error was `approval required ... sandbox_approval is false`, even
  after network and checkout-specific Git write permissions were granted. No
  successful cloud deployment or active hosted URL is claimed.
- The standalone Node/Docker host is provided as an alternative deployable entry
  point. Its container image has not been built locally; Docker is not required
  on the user's PC to deploy it on a cloud container host.

The JavaScript retrieval adapter follows the Python method, but tokenization and
ties may differ. This is a research prototype without validated medical Q&A,
durable server storage, or a production multiuser rate limiter.
