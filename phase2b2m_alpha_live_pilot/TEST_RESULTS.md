# Test and execution results

- Focused live/isolation/containment tests: **22 passed**, zero failures/errors.
- Repository discovery suite: **39 passed**, zero failures/errors.
- An additional historical-interface test selection produced one setup error
  because `active_runner/trial/queue.sqlite` is absent on this frontier; the
  33 other selected tests passed. No historical fixture was recreated or changed.
- Alpha executable: `0.163.0-alpha.11`, SHA-256
  `f7ab009c485749503f8c4bf848d002ed8080e4b2c9a1336e80069327e4ae951a`.
- Existing authentication: ChatGPT login verified; no API key was introduced.
- Live model process entries: 1. Retries: 0. Reviewer model calls: 0.
- Assignment before semantic release: verified.
- Terminal live status: `UNKNOWN`, preserve true, new invocation false.
- Job accounting after termination: total 2, active 0.
- Independent last-message file matched the requested fixed object, but it was
  not accepted because JSONL event-shape evidence was unresolved.
- Fresh destination readback: `UNKNOWN / TASK_RESULT_UNAVAILABLE`.
- Phase 2C entered: false.
