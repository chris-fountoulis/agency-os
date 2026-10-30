# Security policy

agency-os handles company memory: client facts, session transcripts and the text people paste
into prompts. A bug that lets a secret reach disk, git or a client spinout is a security bug.

## Reporting a vulnerability

Email **chris@growthofinfluence.com** with:

- what you found and how to reproduce it (a minimal vault or transcript is ideal; please use made
  up data, never a real credential),
- the version (`agency-os --version`) and your OS and Python version,
- whether you plan to disclose it, and when.

Please do not open a public issue for a security problem. You will get an acknowledgement
within five working days and a plan for a fix after that. Credit is given in the changelog unless
you prefer otherwise.

## In scope

- Credential redaction in session logs and checkpoints (`agency_os/redact.py`) missing a common
  credential shape, or redacting in a way that can be reversed.
- `agency-os spinout` letting a denylisted term, another client's name or a credential shape
  through without the leak check failing.
- `sync/vault-sync.sh` committing a file it should hold back.
- Hooks executing anything derived from note content or transcript content.

## Out of scope

- Secrets a person writes into a note by hand and commits themselves. The tooling reduces the
  risk; it cannot remove it.
- Vault repositories made public by their owners.

## Supported versions

Fixes land on the latest release. agency-os is pre-1.0, so please upgrade rather than expect a
backport.
