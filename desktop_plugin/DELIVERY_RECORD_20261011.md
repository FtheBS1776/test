# Genie Desktop plugin user-delivery record — 2026-10-11

Status: **DELIVERY_ARTIFACT_VERIFIED / INSTALLATION_OPEN**

This record supplements, and does not rewrite, the earlier `ROOT_ADJUDICATION.md`. The earlier adjudication correctly recorded that its ephemeral package was not uploaded. After explicit user approval to prepare an installable package and proceed to the local ChatGPT Desktop connection boundary, a new delivery build was executed and uploaded.

## Authorization boundary

The user explicitly approved preparing the installable Genie package and proceeding toward the local ChatGPT Desktop connection. This authorization covers delivery preparation and the next user-driven local installation/connection step. It does not authorize mutation tools, model dispatch, autonomous continuation, remote hosting, public publication, main merge, promotion, freeze, or EXP010 execution.

## Delivery build

- Repository: `FtheBS1776/test`
- Branch: `nonclaim/genie-desktop-plugin-package-20261011`
- Tested source commit: `41994ac0502100754a74903a49f71945fd47ca3b`
- Workflow run: `38172013213`
- Workflow job: `114566396368`
- Build OS: Windows Server 2025
- CPython: `3.12.10`
- Exact expected runtime/build distribution closure: `36`
- `pip check`: PASS
- Real unfrozen Windows read-only call chain: PASS
- Deterministic integration seed: `host-return-trial-b67b52024e8578e9999c`, 31 files
- Frozen stdio lifecycle: `DESKTOP_PLUGIN_FROZEN_PASS`
- Artifact upload action: `actions/upload-artifact@bbbca2ddaa5d8feaa63e36b76fdaad77386f024f` (`v7.0.0`), pinned by commit
- Upload mode: direct single-file (`archive: false`), so the uploaded artifact bytes are the tested package ZIP rather than a second wrapper archive
- GitHub artifact ID: `11714620713`
- GitHub artifact name: `genie-readonly-windows.zip`
- Retention: 30 days; artifact metadata expiry `2026-11-10T20:24:56Z`

## User-delivery identities

- Windows executable SHA-256: `cc43d546fb19a7330989c2aab390904a07a61d6935a829d035a47b15e83b6f8d`
- Windows executable size: `22131989` bytes
- Install package ZIP SHA-256: `964a8840c7ad48cc23fc2560ee9e63ca85dd50e8691d1a227235c241969fa32e`
- Install package ZIP size: `21836127` bytes

GitHub reported the uploaded artifact digest as exactly `sha256:964a8840c7ad48cc23fc2560ee9e63ca85dd50e8691d1a227235c241969fa32e`. The artifact was then downloaded through the connected GitHub artifact API and independently SHA-256 hashed in the controller environment; the downloaded bytes matched the same digest exactly.

## Package shape

The ZIP contains the portable local plugin folder `genie-readonly/` with:

- root `plugin.json` using Agent Plugins schema `1.0.0`;
- root `mcp.json` using Agent Plugins MCP schema `1.0.0`;
- plugin-relative `./bin/genie-mcp.exe` stdio server.

The package remains read-only and exposes exactly:

- `get_run_status`
- `get_task_result`

No paid hosting, public ingress, system Python installation, manually maintained HTTP server, or remote authentication service is required for the local package.

## Current frontier

The package is now deliverable. The next boundary is **installation on the user's Windows machine and discovery/installation through ChatGPT Desktop's local plugin marketplace**, followed by representative connected verification of exactly the two accepted read-only tools.

OpenAI's current local-plugin documentation supports a personal marketplace at `~/.agents/plugins/marketplace.json`, with plugin content commonly stored under `~/.codex/plugins/<plugin-name>`. ChatGPT Desktop must be restarted after adding/updating a local marketplace before verifying discovery. Actual filesystem changes and Desktop restart occur on the user's machine and cannot be performed by this repository/controller environment.

After connection, verify PASS, CONFIRMED, an unavailable/UNKNOWN path, retained `UNTRUSTED_ACCEPTED_TASK_DATA`, host-managed process lifetime, and no unexpected tool expansion before any further semantic surface is considered.
