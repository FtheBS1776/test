# Test results

- Phase 2B2J decision tests plus the exact retained Phase
  2A/2B1/2B2A-2B2I regression modules: **179 passed**.
- Failures: 0.
- Errors: 0.
- Elapsed test-run time: 19.219 seconds.
- Alpha launches during tests: 0.
- Total alpha launches in this phase: exactly 1, the recorded parser probe.
- Worker/model turns: 0.

Tests enforce the one-launch identity and argument bindings, fail-closed
handling for auth/config drift or process residue, no retry authority, and the
distinction between root-parser rejection and the untested `exec` parser.
