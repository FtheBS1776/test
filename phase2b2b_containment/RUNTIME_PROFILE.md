# Phase 2B2B selected runtime profile — partial, exact, NONCLAIM

Observed host: Windows 10.0 build 22631; platform version 10.0.22621; 64-bit CPython 3.12.14 (`MSC v.1944`). The test host runs the exact Phase 2A venv executable; the child uses the underlying direct runtime executable so the deterministic fixture itself—not an extra venv launcher shim—is assigned before release.

| Bound file | Bytes | Links | SHA-256 |
| --- | ---: | ---: | --- |
| Phase 2A host `python.exe` | 277,808 | 1 | `dcdc8a4ef3c108d7d11f7a8afea50502c8f41763d118f1a94dafc90c74f1614c` |
| Direct child `python.exe` | 107,312 | 1 | `d41bad46673f64e0d02f23797f53f90ccf60f27d6eda8d86dd2d4bbeae5a858c` |
| `python312.dll` | 6,985,520 | 1 | `8bb70bceffd5877733a957b31c392ca027bd2f84230e00de1654f994422fa2af` |
| `python3.dll` | 71,984 | 1 | `0366ee3d630c26ffc27bfab162648ae8c5cadc74b4b46f3e179ca70f4436cab9` |
| `DLLs/_ctypes.pyd` | 131,888 | 1 | `926df1f47c2a782ba154d6824a84aee7197a32eb6b781c2fc33120851e0fb53b` |
| `C:\Windows\System32\kernel32.dll` | 815,520 | 2 | `70f1e69a1d0602ec9e02c713ff2fc1238ddc7fe02ad28fa344954dda446e5236` |
| `C:\Windows\System32\conhost.exe` | 1,044,480 | 2 | `2266b396ef92534a2a2844438df043d4069a2ec47d4e464f55e8c1cd47124a98` |

The runtime checker validates exact absolute paths, bytes, hashes, link counts, and fixture source before the job is created, then revalidates immediately before process entry. It reports the Windows version as an observation; the focused test pins that observation on this host, but the runtime checker does not enforce a portable OS-version claim. The live job member-image query independently observed two child-Python images and two console-host images before termination.

This list is intentionally classified `PARTIAL_SELECTED_RUNTIME_SUPPORT_SET`. It does not enumerate or pin every imported standard-library file, transitive DLL, kernel component, device driver, filesystem implementation, firmware component, or hardware behavior. It is not an attestation or full supply-chain closure.

Codex CLI remains the unchanged Phase 2B2A non-executable plan: version 0.162.1, authentication `NOT_PROVISIONED`, model absent, provider calls zero, and effective tools/MCP inventory `NOT_PROBED`.
