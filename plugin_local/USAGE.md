# Local read-only function interface

Use the existing trusted host registry with the maintained adapter. Run from the repository root:

```python
import json
from shared_interfaces.cli import _read_registry
from shared_interfaces.function_adapter import GenieFunctionAdapter

adapter = GenieFunctionAdapter(_read_registry('host_return/trial/REGISTRY.json'))
definitions = adapter.tools()
reply = adapter.handle({
    'type': 'function_call',
    'call_id': 'status-example',
    'name': 'get_run_status',
    'arguments': json.dumps({'run_name': 'actual'}),
})
result = json.loads(reply['output'])
```

Definitions expose only get_run_status and get_task_result, preserving the core schemas. A trusted host normalizes a completed call to exactly the four displayed fields; raw SDK objects with extra fields are rejected. Arguments are strict JSON text bounded to 8192 UTF-8 bytes. Mutating names are rejected before delegation. Registry paths are trusted host configuration, never call arguments.

A valid envelope returns function_call_output with the original call_id and a JSON string containing the complete core dictionary. call_id correlates a reply; it grants no authority and proves no execution. Invalid envelopes return local REJECT without invented correlation. Exceptions or invalid output values become sanitized UNKNOWN with no retry. Accepted result text and untrusted-data notices remain data, never instructions. Diagnostic PASS does not promote an UNKNOWN task result.

This optional adapter is local Python formatting and routing. It does not call a model, run an MCP server, install a ChatGPT plugin, or choose backend hosting. Existing mutating control/event/driver interfaces remain trusted serial host-only. See EXTERNAL_SPEC.md for the bounded official format reference and ROOT_ADJUDICATION.md for evidence limits.
