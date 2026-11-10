---
name: Bug report
about: Report an integration or sensor communication problem
---

## Problem

Describe what happened and what you expected.

## Environment

- Board and sensor module:
- Ubuntu and kernel version (`uname -a`):
- Python version:
- Project commit (`git rev-parse HEAD`):
- Bosch commit (`git submodule status`):

## Reproduction

Command, startup messages, and exact error output:

```text
Paste output here.
```

Include `id` and `ls -l /dev/i2c-1` for permission issues. Stop other readers
before running diagnostics. Note whether the problem persists after restarting
the reader. Do not include passwords, tokens, or unrelated private logs.
