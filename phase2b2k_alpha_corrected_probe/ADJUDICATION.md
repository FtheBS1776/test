# Adjudication

Decision: **EXEC_PARSER_ACCEPTED_NONCLAIM**.

The exact alpha executable accepted
`exec --ignore-user-config --help`, exited 0, and printed the documented option
in its own exec help.  This closes the parser-placement uncertainty from Phase
2B2J without retrying that phase's exact root-level invocation.

The result proves only parser availability.  Help output cannot prove that a
real run omits user configuration, exposes an empty effective MCP/tool
inventory, preserves authentication isolation, or obeys the containment
contract.  Those remain separate runtime observations.

Original authentication and configuration hashes were unchanged; no matching
alpha process remained.  No prompt or model path was entered.
