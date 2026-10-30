<p align="right"><a href="../README.md">Back to README</a></p>

# Methodology

How agency-os was built, where its rules come from and how we know it works. Short version: it
was extracted from a vault a real team uses every day, every rule maps to a failure we kept
hitting, and every claim in the README is either tested or measured.

- [Where it comes from](#where-it-comes-from)
- [What was generalised and what was left out](#what-was-generalised-and-what-was-left-out)
- [Where the lint rules come from](#where-the-lint-rules-come-from)
- [How it is tested](#how-it-is-tested)
- [Continuous integration](#continuous-integration)
- [What was measured](#what-was-measured)
- [Limits](#limits)

## Where it comes from

[Growth Of Influence](https://growthofinfluence.com) runs its company memory as one Obsidian
vault of about 900 notes. Clients , projects, SOPs, decisions and meetings live there along with
an open loops register and per-person session logs. Several team members' vaults were merged
into it. The team works in it daily through Claude Code : every session reads the vault before it
starts and writes back what it learned.

agency-os is the machinery of that vault taken out and made general. The folder spine, the four
hubs, the capture protocol, the hooks, the linter, the index, the client spinout and the git sync
all ran in production first.

## What was generalised and what was left out

| Kept: the mechanism | Removed: the business |
|---|---|
| Numbered folder spine, four hubs, MOC per folder | Every real client, project and person |
| `CLAUDE.md` structure and the "update facts in place" rule | The company's own rules, prices and decisions |
| The capture protocol (`vault-autopilot.md`) | Anything that names a tool stack, server or account |
| Hook behaviour: briefing, session log, checkpoint | Real transcripts and real session logs |
| Lint checks, index format, spinout scrub, sync safety rules | Hard-coded hub, folder and MOC names, now settings in `agency-os.json` |

The template vault describes a fictional agency , Northwind Studio, with three clients and five
people. It exercises every feature: open loops with one overdue, decision records , session logs,
a client with a project and a meeting , an archived note.

> [!NOTE]
> The production vault itself is private. What is public is everyting needed to build your own.

## Where the lint rules come from

Each check exists because the failure it catches showed up in the production vault, usually
written by a Claude Code session in a hurry.

| Failure seen in production | Check | Why it matters |
|---|---|---|
| Notes nobody links to, invisible in the graph and to the next session | `orphan` | A fact no one can reach is a fact that gets written again, differently |
| `[[links]]` to notes that were renamed or never created | `broken-link` | The next session follows the link and finds nothing |
| Notes called `Untitled`, `Notes`, `Misc` | `generic-name` | Search and backlinks become useless; sessions cannot tell what a note is about |
| Empty notes left behind by an aborted capture | `empty` | They look like knowledge and hold none |
| Notes with no parent node | `no-hub` | The graph loses its spine and notes float |
| Two notes with the same name after merging vaults | `duplicate-title` | Links resolve to the wrong one without any error |
| Missing or inconsistent frontmatter | `frontmatter` | Type and status filters miss the note |
| Notes added to a folder but not to its MOC | `moc` | The map stops matching the territory |

The thresholds are deliberately strict: the template vault lints with zero findings and CI uses
`--strict`, so any warning fails the build.

## How it is tested

The suite is 90 tests on the standard library `unittest`, with nothing to install.

| Area | How |
|---|---|
| Template vault | Lint has no findings at all, the generated index is current, every note has a summary, the folder skeleton and all seven templates exist, the Obsidian JSON is valid |
| Lint | A fixture vault (`tests/fixtures/broken-vault`) with planted errors: a broken link, an orphan, a missing hub link, an empty note, an `Untitled` note, bad frontmatter, a duplicate name, MOC gaps. The test asserts the exact totals, 11 errors and 5 warnings, plus exit codes, JSON and GitHub annotation output |
| Hooks | Realistic Claude Code hook payloads (`session_id`, `transcript_path`, `cwd`, `hook_event_name`, `stop_hook_active`, `agent_id`, `trigger`) and a JSONL transcript fixture with tool results, a subagent turn and a planted credential. The plugin launcher is run as a subprocess with JSON on stdin, the way Claude Code runs it |
| Redaction | GitHub tokens, cloud keys, URL credentials and keyword-anchored values, with test values built by concatenation so secret scanners do not trip on the repository |
| Spinout | Every denylist source, credential redaction, selection and exclusions, a lint clean result, a report that never names the terms, and a planted leak the verifier must catch |
| Sync | `vault-sync.sh` against a real bare git remote and two clones: push, pull, rebase, an index-only conflict that resolves itself, a real conflict left for a person, held-back large files and secrets, the pause file, the debounce |
| Scaffold | `init` with and without examples is lint clean, refuses to overwrite, keeps an existing `CLAUDE.md`, merges hook settings once |
| README | The stats and lint blocks in the README are regenerated and compared verbatim |
| Repository | No em or en dash in any text file, executable bits on the scripts |

> [!TIP]
> Run it yourself: `python3 -m unittest discover -s tests`. About 30 seconds on a laptop.

## Continuous integration

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) has two jobs.

| Job | Runs on | What it does |
|---|---|---|
| `test` | Python 3.9 and 3.12 on Ubuntu 24.04, Python 3.12 on macOS | The full unit test suite |
| `vault` | Python 3.12 on Ubuntu | Installs the package with pip, lints the template vault with `--strict --format github`, checks the index, prints stats, scaffolds two fresh vaults and lints them, spins out a client vault and lints that |

The `vault` job tests the installed package, not the checkout. That is what catches a template
file missing from `pyproject.toml`.

## What was measured

| Measurement | Result |
|---|---|
| `agency-os lint` on the production vault, 935 notes | about 1 s |
| The same vault after it grew to 1,165 notes | about 1.8 s on a laptop |
| `agency-os lint` on the 35-note template vault | about 0.2 s |
| Full test suite, macOS laptop | about 33 s |

Most of the lint time is reading files. Link resolution is a dictionary lookup by note name, so
the cost grows with the size of the vault and not with the square of the note count. The
SessionStart briefing runs one lint pass, so its cost tracks these numbers. The Stop hook reads
at most the last 4 MB of the transcript.

## Limits

> [!WARNING]
> Redaction and the spinout scrub match patterns and names. They cannot judge whether a sentence
> is sensitive. Read a client vault once before you share it.

- **Frontmatter is a flat YAML subset.** Keys and lists parse; nested maps and multi-line strings do not.
- **Links resolve by note name.** Two notes with the same name are reported as `duplicate-title`
  and the link goes to the one in the linking note's own folder.
- **Plugin syntax is not understood.** Dataview queries and other plugin blocks are treated as
  plain text.
- **Team names are not scrubbed by default** in spinouts. List them in a denylist file.
- **The sync rebases, it does not merge prose.** Two people editing the same lines get one
  notification and resolve it by hand.
- **Windows needs one edit.** The plugin's hook commands call `python3`. See the
  [FAQ](faq.md#does-it-work-on-windows).
- **No `--fix` yet.** Lint reports, you or a session repair. It is the first item on the roadmap.

Interested in how the rest of the agent tooling market approaches this? Growth Of Influence
keeps a public [map of AI agent companies](https://growthofinfluence.com/ai-agent-companies/).

---

<p align="right"><a href="../README.md">Back to README</a></p>

<p align="center">Built by <a href="https://chrisfountoulis.com">Chris Fountoulis</a> at <a href="https://growthofinfluence.com">Growth Of Influence</a>.</p>
