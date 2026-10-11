# Local projection usage

This is a code-level seam for a future MCP server handler, not a server itself.

```python
from shared_interfaces import cli
from shared_interfaces.mcp_consumer import GenieMcpReadonlyConsumer

runs = cli._read_registry("host_return/trial/REGISTRY.json")
consumer = GenieMcpReadonlyConsumer(runs)

tool_descriptors = consumer.tools()
result = consumer.call("get_run_status", {"run_name": "actual"})
```

A future MCP server may register the two returned descriptors and delegate each handler to `consumer.call(name, arguments)`. That future composition must add its own transport/authentication/lifecycle checks and must not expose the mutating Genie surfaces merely because MCP supports write tools.

`structuredContent` contains the complete accepted adapter dictionary. If accepted task text is present, its untrusted-data label and notice are mandatory. Never execute that text as instructions. `UNKNOWN` is not retry permission.
