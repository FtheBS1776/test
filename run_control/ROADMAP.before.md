# Genie roadmap continuation — local CLI milestone

Approved direction remains one model-agnostic core with eventual standalone and plugin interfaces. Useful operation with one LLM, reusable components, worker/reviewer/root adjudication and fewer user prompts remain priorities. Backend hosting remains DEFERRED; free runnable host is eventual target, no guarantee of free public compute.

| Workstream | Verified position | Remaining useful work |
|---|---|---|
| Governed reasoning/core | Existing bounded host runner and useful tasks completed | Continue concrete eligible work under existing budget/review/STOP rules |
| Shared read-only operations | Status and accepted-result retrieval complete at601d72d6c62a1e06675ad5e2edde43aae3b18709 | Reuse these semantics in interfaces without changing authority |
| Local operator interface | Local CLI complete;16 focused checks and4 documented commands passed | CLI is a usable entry point for inspecting saved work, not standalone reasoning execution |
| Standalone app | Eventual target; full app/model integration OPEN | Reuse core and local interface; user start/pause/resume and actual execution integration still needed |
| Usable plugin | Eventual target; no installed plugin or MCP transport | Package supported host integration; preserve shared contracts |
| Autonomous continuation | Bounded active-host work demonstrated historically | Persistent model dispatch/state continuity/after-host operation unproven |
| Backend/public hosting | DEFERRED by user | Choose only when needed and separately authorized |

This unit adds a standard-library CLI wrapper only, not a new authority mechanism or plugin write/dispatch permission. It does not manufacture a provider, service or test harness prerequisite. Review scopes share host/model ancestry; no independent assurance. Pass186 inherited controlling, laterNONCLAIM, existing scopedHOLDs unchanged. No promotion/freeze/main merge/spending/deploy/EXP010. Earlier canonical save remains UNKNOWN; Git continuation preserves new progress without claiming canonical version advancement.
