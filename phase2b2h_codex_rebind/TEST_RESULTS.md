# Codex upgrade/rebind test results

## Installation and offline verification

- Pre-upgrade binding: `codex-cli 0.162.1`, 333,479,728 bytes, SHA-256
  `dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`.
- The documented `codex update` command returned
  `Could not detect the Codex installation method` before any package change.
- Fresh post-attempt readback matched the exact pre-upgrade size, hash, and
  version.
- npm registry `latest` resolved to 0.162.1 with the recorded package integrity;
  no newer stable package existed to install.
- The app-server-daemon cache contained one other official local candidate; it
  matched the bound executable byte-for-byte.
- Offline `--ignore-user-config --version` parsing exited 2 with
  `unexpected argument`; no app server, prompt, or model was started.
- The alpha tag was observed but not downloaded, installed, or selected.

## Regression

The exact inherited 161-test Phase 2B2 manifest plus five new fail-closed
rebind-decision tests passed: **166/166, zero skips**.

The new tests reject a missing stable replacement, reject an implicitly
selected prerelease, reject a byte-identical candidate as a rebind, require a
distinct supported stable candidate, prevent a successful rebind from
authorizing process launch, and statically exclude install/launch/network/auth
capabilities from the decision module.

No authentication operation, credential read/copy, app-server process entry,
logical operation, inventory protocol, model turn, Genie mutation, reviewer
progression, or Phase 2C activity occurred.
