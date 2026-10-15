# Test results

- Interpreter: isolated Phase 2A test environment, bytecode writes disabled.
- Scope: Phase 2B2I decision tests plus the exact accepted Phase
  2A/2B1/2B2A-2B2H regression modules.
- Result: **174 tests passed, 0 failures, 0 errors**.
- Elapsed test-run time: 18.985 seconds.
- Alpha executable launches: **0**.
- Install operations: **0**.
- Worker or model turns: **0**.

The decision tests cover successful static nomination and rejection for
unverified registry integrity, unsafe paths, lifecycle scripts, invalid or
unexpected signing identity, missing flag literal, duplicate executable
identity, and prohibited launch/network/secret capabilities in the pure
decision module.
