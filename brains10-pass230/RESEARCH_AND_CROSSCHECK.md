# Primary-source research and cross-check before repair

Retrieved 2026-10-02. Initial broad search returned irrelevant results and supplied no evidence; direct primary sources below used instead.

- https://docs.github.com/en/actions/tutorials/use-containerized-services/use-docker-service-containers : ephemeral services, Ubuntu requirement, mapped ports and default image entrypoint/command. Confirms host endpoint availability is distinct from internal health. Original startup remains under-specified; not reported as a reproduced image defect.
- https://etcd.io/docs/v3.6/op-guide/container/ : official example explicitly supplies executable, client/peer listen and advertise addresses. No reliance on container defaults warranted.
- https://etcd.io/docs/v3.6/install/ : official release binaries supported. A native process from the same checksum-pinned archive supplies the required actual etcd implementation without a second container-image identity. This is a documented harness adaptation, not a provider substitution claim.
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow : workflow_dispatch requires default-branch workflow, and supports selecting a branch. Preserve manual trigger. A branch-only commit is preparation, not execution.
- https://docs.github.com/en/actions/reference/security/secure-use : full commit pins, minimum permissions, same runner common-cause effects. Use contents:read only and persist-credentials:false. No secrets, OIDC or attestation needed.
- https://docs.github.com/en/actions/tutorials/store-and-share-data : artifact SHA256 verification can merely warn. Independent controller must reject mismatch, and independently verify complete manifest/run binding.
- https://etcd.io/docs/v3.6/learning/api_guarantees/ : default linearizability, serializable reads may be stale, multi-key Txn has one revision, timeouts leave completion uncertain. A healthy single member cannot test stale follower/failover behavior or unknown commit. Compare returned exact-key revisions after completion/replay; do not infer stronger claims from sequential equality.
- GitHub REST release v3.6.5 reports linux-amd64 archive digest 66bad39ed920f6fc15fd74adcb8bfd38ba9a6412f8c7852d09eb11670e88cac3, matching previously downloaded bytes. This is same-publisher distribution integrity, not independent administrator trust. Pinned 3.6.5 is chosen for continuity with verified actual-client tests; no latest-release claim.
- actions/checkout tag v6 resolved via official repo to d23441a48e516b6c34aea4fa41551a30e30af803. Its action.yml supports persist-credentials:false and uses node24. actions/upload-artifact v4 resolved to ea165f8d65b6e75b540449e92b4886f43607fa02; action.yml supports error on missing files, no overwrite, outputs artifact-digest. Only interface inspected; not a full action implementation audit.

Cross-check of initial findings against external sources:
RETAIN file-presence != hash verification and gate framing/output retention defects.
RETAIN bounded timeout/failure evidence needs; cancellation/runner loss may still prevent artifact return and must be INDETERMINATE.
NARROW container startup diagnosis to unverified host reachability, not proven failed official image. Avoid seam with explicit native loopback server and client from one pinned release.
RETAIN original Pass230 independently provisioned purpose remains HOLD. New evidence scope explicitly single-node implementation conformance, using R2 repaired gate unchanged and labelled distinctly.
RETAIN shared runner/operator trust limitation; do not add signatures, OIDC or a new authority registry.

Decision: GitHub-hosted ephemeral native etcd is ADEQUATE_FOR_BOUNDED_IMPLEMENTATION_OBSERVATIONS, subject to exact identity/completeness checks. It is NOT ADEQUATE for original independent-provider trust premise. Proceed with separately bound repaired harness. A local rehearsal is engineering evidence only, never a GitHub run.

Operational inspection: FtheBS1776/test is public and contains the prior R2 provider-capture workflow. FtheBS1776/R1 is private and contains the EXP010 executor. Do not publish newly uploaded inputs to public test based solely on their presence in this chat. No GitHub workflow-dispatch tool or configured CLI/token is exposed. Browser fallback requires user approval under tool instructions. Preparation and local validation can finish first.
