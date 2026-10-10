# Shared read-only status tool

This is a transport-neutral Python component for future standalone and plugin interfaces. It is not an installed MCP plugin or server. The trusted host chooses an explicit alias registry; the model-facing input contains only a run name. Do not expose host configuration or all private runs to arbitrary users. Remote user authentication/authorization and hosting remain deferred.

From the repository root, the following reads this completed unit using the maintained component, with no model call or store mutation:

```bash
python3 -B - <<'PY'
import json
from shared_interfaces.status_tool import GenieStatusTools
host = GenieStatusTools({'current': {
    'queue': 'shared_interfaces/trial/queue.sqlite',
    'run_id': 'genie-shared-status-interface-run-20261010',
    'owned_root': 'shared_interfaces/trial/work',
}})
print(json.dumps(host.call('get_run_status', {'run_name': 'current'}), sort_keys=True))
PY
```

`tools()` returns the single-tool schema and read-only annotations for a future transport wrapper. `call()` returns the existing diagnostic dict. Unknown tools, argument fields/types or aliases reject before accessing core stores; source mismatch and core errors are sanitized. Run aliases are trusted-host lookup names, not caller paths. For an application with changing working directories, configure absolute host paths. Registry records are detached strings, not remote authorization evidence or hostile-path capabilities.

Visible output includes run/task identities, workflow state/attempt, journal agent/call identity/count, historical budget/stop and fresh local sink states. No candidate text, observation evidence bodies, configured filesystem paths or raw exception messages are returned. Top-level PASS means the diagnostic ran; inspect per-task fresh_sink and preserve UNKNOWN/MISMATCH. Source pinning reuses existing dependency behavior; no hostile runtime/module substitution protection, global snapshot, remote authenticity, rollback continuity or always-on execution is established.
