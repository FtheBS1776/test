# Recovery live postmortem

Two independent evidence gaps caused the fail-closed result:

1. The exact disabled-feature configuration generated a structured `error` item:
   code mode was unavailable because the code-mode host was disabled. The model
   still returned the required data object and made no tool call, but an error
   item was outside the accepted live event contract.
2. The monitor retained process handles but deferred image-path lookup until
   after both members exited. Windows then returned error 31 from
   `QueryFullProcessImageNameW`, so exact live member identities were not durable.

The recovery repair succeeded in retaining raw streams, making the event cause
fully diagnosable. A future design would need to snapshot image identity at first
observation and explicitly adjudicate the exact fail-closed code-mode event.
Neither change can reclassify or replay this operation.

