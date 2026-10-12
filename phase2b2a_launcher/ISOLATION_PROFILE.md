# Phase 2B2A isolation profile — fixture real, Codex deferred

## Executed fixture profile

The real local Windows test launches only:

```text
<exact phase2a python.exe> -I -S -B <exact no_model_fixture.py> --mode <closed fixture mode>
```

The request is canonical UTF-8 JSON on bounded stdin. It never appears in argv. The launcher does not add the launch ID to child input; caller-provided opaque strings can contain any bytes allowed by the schema. The child starts below a new `genie-phase2b2a-*` temporary root outside every Git repository. Its environment is rebuilt from an allowlist and excludes `PATH`, `HOME`, `USERPROFILE`, `CODEX_HOME`, API keys, and Genie tokens. The committed claim is observed as `CLAIMED` at process entry.

The child response is bounded on stdout/stderr, strict UTF-8/JSON with duplicate and nonfinite rejection, exact-field checked, and bound to request, stdin, argv, environment keys, cwd repository status, `model_invoked:false`, and `proposal:NO_MODEL_CALL`. These checks establish only behavior of the exact deterministic fixture in the tested local environment.

This is process separation, not hostile sandboxing, containerization, network confinement, or filesystem confinement. The launcher makes one direct-child kill-and-bounded-reap attempt on uncertainty and reports cleanup failure as `UNKNOWN`; descendant process-tree control is not implemented. Parent request content is structurally bounded but semantically unverified. The interpreter executable and fixture are pinned and rechecked near use, while concurrent same-user path replacement and the complete runtime/OS closure are not controlled.

## Deferred Codex profile

Codex CLI 0.162.1 at the inspected local absolute path is hash-bound. The returned plan uses headless `codex exec`, stdin (`-`), `--ignore-user-config`, `--ignore-rules`, `--ephemeral`, `--strict-config`, `--sandbox read-only`, an output schema/result path placeholder, and explicit disables for plugins, apps, multi-agent, browser/computer, shell, hooks, image, workspace-dependency, and related capabilities.

OpenAI's headless Codex guidance supports stdin plus `--output-schema` and recommends pinning the CLI version; OpenAI's agent security guidance recommends workload isolation, restricted network access, and keeping application credentials outside the child environment. Those references informed the plan. They do not prove this future child profile effective.

- https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex
- https://developers.openai.com/api/docs/guides/agents-api/environments/security

The Codex plan was never executed. Authentication is `NOT_PROVISIONED`, model selection is absent, provider usage is zero, and effective tool inventory is `NOT_PROBED`. A live Codex worker or reviewer remains outside Phase 2B2A.
