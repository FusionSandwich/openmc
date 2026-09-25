# StellarCSG verified savepoints

`periodic_axis_openmc_adapter_source.zip` was intended to be the complete source
and test snapshot for the periodic-axis milestone. The blob committed at
`9adb7c4bd8a97c88f4a4e614b80637d6043c202b` is truncated and must not be used.

`periodic_axis_openmc_adapter_milestone.patch` was intended to be the
corresponding one-commit patch. It is also truncated and must not be used.

The declared source archive SHA-256 was:

```text
5043bcd871b07067468ca9ba094e6da4b9fb2cc03f21f714248c71f1a9ecc44a
```

The declared patch SHA-256 was:

```text
7f89f70568283868eeb91954c2aeae2fa207b4ccddffc7aa03daa284704fc922
```

The observed source blob is 15,008 bytes with SHA-256
`4800cfc48bb575835489c05b42e29c10ccac4a182987156f8b6e6fb30e2f5241`.
The observed patch blob is 7,892 bytes with SHA-256
`5b41cb1bf0d0ff81da39d76552418a4fdf4d93f55bebeff71abdd3ca86989782`.
`../tools/restore_verified_milestone.py` therefore rejects the archive as
designed.

The source now present in `dev/stellarcsg` was recovered from the earlier
hash-valid v2 materialization bundle at commit
`913860056e3653b24b72b9fca4fe4245b7538c08`. Its decoded tarball is 73,624
bytes with SHA-256
`35e89d84cf821d842a0cc42537c4b3fe1ae11a099a97f92c1043c79ac8e1e6ae`.
GitHub Actions run `33297036204` independently verified and extracted that
bundle; the run failed only at the later whitespace check. See
`../reports/HANDOFF_RECOVERY_REPORT.md` for commands and test evidence.
