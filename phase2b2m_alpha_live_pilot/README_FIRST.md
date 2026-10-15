# Phase 2B2M: one alpha live worker pilot

This directory contains the one-shot launcher, fresh synthetic task, tests, and
durable evidence for the authorized NONCLAIM live pilot. The one permitted turn
has already run. **Do not run `provision_synthetic.py` or `run_live_pilot.py`
again.**

The launcher uses the audited alpha `codex.exe`, existing ChatGPT/Codex
authentication, `exec --ignore-user-config`, an empty MCP override, disabled
authority/tool features, a read-only sandbox, and an isolated scratch directory.
The prompt is released only after Job assignment is verified.

The terminal status is `UNKNOWN`, not success. The independent last-message file
matched the fixed schema, but the JSON event shape could not be authoritatively
reconciled and the failure path had not retained raw JSONL. The result was not
submitted or accepted. The durable operation forbids a retry. This does not
establish general sandboxing, independent provenance, or Phase 2C readiness.
