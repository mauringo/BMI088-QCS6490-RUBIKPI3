# Contributing

Keep source code, comments, user-visible messages, and documentation in English.

## Local setup

1. Clone recursively, or run `git submodule update --init --recursive`.
2. Install a C compiler, make, Linux I2C headers, and Python 3.10 or newer.
3. Run `make` and `make test` without root.

No pip dependencies are needed. Do not commit generated binaries, Python caches,
local logs, or machine-specific configuration.

## Changes and verification

Describe the problem and resulting behavior in each pull request. Include test
results and clearly distinguish hardware tests from tests with mocked hardware.
The default test suite must not touch `/dev/i2c-*` or require a connected sensor.

Changes to initialization, transport, reset handling, or scaling should also be
verified on hardware when available:

```bash
sg i2c -c 'make hardware-test'
```

Stop any existing reader first. The test resets the sensor and checks repeated
initialization, changing accelerometer values, exclusive access, and cleanup.
Do not weaken error handling to make a hardware test pass. Report the operation,
I2C address, register, kernel version, and startup output when diagnosing failures.

Keep the C and Python clients on the same shared backend. Preserve the context
manager lifecycle, handle locking, physical units, and the documented sampling
limitations. Never make device nodes world-writable or require a root reader.

## Updating Bosch sources

Do not patch files inside the submodule as part of an unrelated change. To update
it, select and review an upstream commit, run build/software/hardware checks,
and update the pinned commit references in `THIRD_PARTY_NOTICES.md` and the guide.
Commit the new gitlink with the integration changes. An upstream update is not
validated merely because it compiles.

## Documentation

Keep the README focused on first use. Put detailed explanations and board-specific
observations in `docs/guide.md`. Preserve upstream licensing and attribution.
