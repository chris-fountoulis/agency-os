# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-30

First public release.

### Added

- Template vault for a fictional agency, Northwind Studio: numbered folders, a company node
  above four hubs (Management, Product, Sales, Marketing), MOCs, a Vault Guide for Claude Code
  sessions, an open loops register, decision records, example clients, projects, meetings and
  session logs, seven templates, and Obsidian settings with a navy and gold CSS snippet.
- `CLAUDE.md` template and `vault-autopilot.md`, the capture protocol.
- `agency-os` CLI, standard library only, Python 3.9 to 3.13:
  - `init` scaffolds a vault, `CLAUDE.md` and the protocol, optionally without examples or with
    project hooks;
  - `lint` checks broken links, orphans, hub links, empty and generic notes, frontmatter,
    duplicates, MOC membership and an optional dash rule, with text, JSON or GitHub Actions
    annotation output and exit codes;
  - `index` generates a deterministic All Notes Index, with `--check` for CI;
  - `stats` reports size, link density, orphan rate, hub coverage and activity;
  - `loops` lists open and overdue loops;
  - `spinout` builds a standalone sanitised client vault and fails on any leak;
  - `session-log`, `checkpoint` and `context` back the Claude Code hooks.
- Claude Code plugin: SessionStart briefing, Stop session log, PreCompact checkpoint, and the
  `capture`, `open-loops` and `vault-health` skills, and a plugin icon. The repository is also a
  single-plugin marketplace.
- `sync/`: git sync script that holds back large files and credential-shaped lines and resolves
  conflicts that only touch the generated index, with launchd and systemd templates and an
  installer.
- Documentation: architecture, team setup, client vaults, FAQ.

[0.1.0]: https://github.com/chris-fountoulis/agency-os/releases/tag/v0.1.0
