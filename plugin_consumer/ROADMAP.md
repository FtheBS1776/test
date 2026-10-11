# Plugin-consumer roadmap addendum

Completed in this bounded unit: consumer-side normalization/return contract over the accepted read-only function adapter.

The next actual plugin step is now narrower: implement a minimal MCP server/transport that exposes these exact two read-only tool contracts without changing their meaning, then connect it through a supported ChatGPT plugin path and verify actual installed operation. That later step must separately address the concrete host/deployment/tunnel and any authentication boundary it chooses.

Do not add write tools or model dispatch merely because MCP supports them. Mutating Genie operations remain trusted serial-host only until separately scoped and reviewed.

The larger amendment frontier also remains open: reduce routine manual model/tool bridging and demonstrate useful continuation through a real host mechanism. A read-only plugin surface improves observability/usability but does not itself solve autonomous dispatch or after-host continuity.

Pass186 remains inherited controlling; this interface work remains NONCLAIM. Backend hosting is still deferred by user direction.
