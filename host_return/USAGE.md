# Current-host stream entry

The accepted [entry](../shared_interfaces/work_host.py) supplies an explicit registry/run to the existing [driver](../shared_interfaces/session_driver.py). It reuses the exact [registry reader](../shared_interfaces/cli.py), leaving the read-only CLI unchanged. The host still supplies actual worker returns and separately adjudicated review decisions. This module installs no model API, plugin service, backend or after-host runtime.

Mutating invocation for an existing authorized trusted serial run:

```sh
python3 -B -m shared_interfaces.work_host --registry /absolute/owned/registry.json --run authorized-alias --max-actions 64
```

The registry retains the existing queue/run_id/owned_root mapping. Relative paths anchor to the resolved registry target's parent; the run alias is explicit. Do not supply an old emitted worker action as new permission. `--max-actions` accepts1..128 and defaults64; it is a local progression guard, not an author-budget reset. Duplicate/unknown/abbreviated options and invalid configuration reject before entry. This compact entry has no help mode; inspect this document and source before invoking it.

Exit codes:0 only STOP/ALL_TASKS_COMPLETE,2 REJECT,3 UNKNOWN,4 other terminal. Exit0 is local progression status, not truth/authenticity/whole-system acceptance; fresh task results remain necessary. Entered exceptions preserve UNKNOWN and never become setup rejection. No restart/refund/replacement or stream resynchronization is provided. A failed output can prevent any terminal message; inspect the nonzero return and preserved original state.

For the current Work command tool, ordinary pipes returned EOF in the earlier run. A new tty:true session remained live and accepted separately supplied stdin. The recorded fresh trial uses short ASCII messages: actual serialized returns are checked before submission against the narrow3900-byte trial guard. This is not proof of all160000-byte valid driver payloads through a terminal, an IO deadline or hostile IPC. Terminal input echo is not a driver receipt. Original driver stdout and consumed stdin are separately logged by the root-owned trial launcher.

The root controller translates emitted fresh requests into supported Work author/reviewer tools and feeds bound replies. The driver sequences observe,submit,review,freshdelivery and the next authorized task without an hourly gate or extra user prompt. Root labor remains; this is not Python calling a provider model by itself. A restarted WAITING/REVIEW run reconciles without external hook replay. See the earlier [pending guide evidence](../session_driver/TRANSPORT_BLOCKER.md); that run remains untouched.

[Plugin routing inventory](PLUGIN_ROUTING.json) maps existing callable surfaces for future consumers. It does not install a plugin or expose mutating interfaces remotely. Host owns configuration; remote authentication/concurrency/always-on/after-host operation remain unresolved. Backend is deferred. Pass186 controlling, laterNONCLAIM, scopedHOLDs preserved; no promotion/freeze/mainmerge/spending/deploy/EXP010. Same-model ancestry and unmeasured root effort/cost retained.
