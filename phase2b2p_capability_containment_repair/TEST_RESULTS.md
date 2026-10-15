# Test results

- Focused repair contract: 8 passed, 0 failed.
- Repository package-aware discovery: 56 passed, 0 failed.
- Fresh Windows no-model containment fixture: verified.

An exploratory raw-path invocation across heterogeneous historical test files
was not a valid repository suite.  Those files require different interpreters,
working directories, optional SDKs, Windows privileges, or POSIX facilities;
its failures are therefore excluded from adjudication.  The two timeout
processes and their identified temporary directories were confirmed gone and
removed.  The supported package-aware discovery command is authoritative for
this branch.
