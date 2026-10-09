# Author attempt 1

Task: genie-checkpoint-input-bound-20261009
Input SHA-256: 6e32a58ea469a836c2326206ed64d3e7317bd85020f409b1636643f79ca826d9
Attempt: 1
Candidate: checkpoint_maintenance/candidate/verify_checkpoint_1.py
Candidate SHA-256: 0bd9fe288cfb051fc6ba779bce5e428a5ee9a74b5f3f8ba4bf972bf98d437e28
Candidate UTF-8 bytes: 6992

Started from the exact baseline SHA-256 6b3c01c598e904c9aa171d7b22995cd0eb918db2c9cabf289c1003987db737b6. Changes add the independent 64 MiB compressed cap, nonblocking single-descriptor open, regular-file and initial-size fstat checks, and counted reads limited to remaining capacity plus one sentinel byte. Existing anchor check and subsequent ZIP verification remain unchanged. Unbuffered opening avoids hidden buffering read-ahead beyond each counted request.

Own checks: read the contract, frozen root test source and baseline reproduction; verified baseline hash and saved dispatch task/input/exact integer attempt correspondence; applied a single asserted baseline block replacement and two import/constant insertions; computed candidate hash and byte length. Candidate was not imported, executed or compiled, and no tests were run by the author. Root execution remains separate.

Caveats: ordinary trusted serial host filesystem scope; no immutable snapshot, I/O deadline, CPU-time bound, pre-limit central-directory allocation, hostile-process confinement, cross-platform FIFO guarantee or authenticity claim. Symlinks to regular files remain allowed. Later ZIP reads use the same descriptor but this change does not claim protection against concurrent modification after hashing. Maintained verifier and comparison pins were not modified by the author.
