<p align="right"><a href="../README.md">Back to README</a></p>

# FAQ

Short answers to the questions people ask first. The longer story is in
[architecture.md](architecture.md) and [methodology.md](methodology.md).

- [Is this a second brain template?](#is-this-a-second-brain-template)
- [Do I need the plugin?](#do-i-need-the-plugin)
- [Do I need Obsidian?](#do-i-need-obsidian)
- [Will the hooks slow my sessions down?](#will-the-hooks-slow-my-sessions-down)
- [What if a session writes a broken link or forgets frontmatter?](#what-if-a-session-writes-a-broken-link-or-forgets-frontmatter)
- [Can it leak secrets into git?](#can-it-leak-secrets-into-git)
- [Why update facts in place instead of appending?](#why-update-facts-in-place-instead-of-appending)
- [Why four hubs?](#why-four-hubs)
- [Can different clients get their own vaults?](#can-different-clients-get-their-own-vaults)
- [Does it work on Windows?](#does-it-work-on-windows)
- [How big can a vault get?](#how-big-can-a-vault-get)

### Is this a second brain template?

It is a company brain. Personal second-brain setups optimise for one person's thinking. An
agency needs the opposite: one memory that five people and every Claude Code session share,
with rules about what goes where, who wrote what and what must never leave the building. The
structure (four hubs, MOCs, open loops register, decision records) and the tooling (lint, session
logs, client spinouts) are built for that.

### Do I need the plugin?

No. The plugin is the shortest path: it adds the three hooks and the `/agency-os:capture`,
`/agency-os:open-loops` and `/agency-os:vault-health` skills. Without it, `agency-os init --hooks`
writes the same hooks into `.claude/settings.json`, and the CLI works on its own from a checkout
(`python3 scripts/agency-os`) or a pip install (`agency-os`).

### Do I need Obsidian?

The vault is plain Markdown with `[[wikilinks]]`, so everything works without it: Claude Code
reads and writes the files, lint and the index run anywhere. Obsidian is how people browse it:
the graph, backlinks, the Home dashboard, templates.

### Will the hooks slow my sessions down?

The SessionStart briefing parses and lints the vault once. On the production vault this was
extracted from that took about 1 s at 935 notes; the 35-note template vault takes about 0.2 s.
Most of it is reading files. The Stop hook reads the tail of the transcript (at most 4 MB) and
appends a few lines. Every hook has a timeout and exits 0 on any error. Measurements are in
[methodology.md](methodology.md#what-was-measured).

### What if a session writes a broken link or forgets frontmatter?

That is what lint is for. The capture skill ends with a lint run, the SessionStart briefing
reports the lint state, and CI can block a push with errors. Session logs themselves cannot break
lint: unresolvable links in them are written as plain text.

### Can it leak secrets into git?

Three layers stand in the way. The session logger redacts credential shapes before writing, the
sync holds back any file whose new lines look like a credential and the protocol tells sessions
to record where a credential lives, never its value.

> [!WARNING]
> None of them is a substitute for not pasting secrets into prompts.

### Why update facts in place instead of appending?

Because the next session reads the note, not its history. A note that says "budget is X" and,
three paragraphs later, "update: budget is now Y" forces every reader to work out which one is
current, and sessions get it wrong. One current version per fact; git and the session logs keep
the history.

### Why four hubs?

Every note needs one obvious parent so the graph has a spine and nothing floats. Management,
Product, Sales and Marketing cover an agency without overlap, with a tie-breaker order (Sales,
Product, Marketing, Management) for notes that could sit under two. Change them in
`agency-os.json` if your company is shaped differently.

### Can different clients get their own vaults?

Yes, with `agency-os spinout`. See [client-vaults.md](client-vaults.md).

### Does it work on Windows?

The CLI and hooks are pure Python and run anywhere Python 3.9+ runs. The plugin's hook commands
call `python3`; on Windows, where the launcher is often `python` or `py`, use
`agency-os init --hooks` and edit the command in `.claude/settings.json`. The sync script needs
bash and git (Git Bash works); the background job templates are for macOS and Linux.

### How big can a vault get?

The production vault this was extracted from is about 900 notes across several merged sub-vaults
and lints in about a second, most of it disk reads. Link resolution is a dictionary lookup, so
nothing here is quadratic in the number of notes.

---

<p align="right"><a href="../README.md">Back to README</a></p>

<p align="center">Built by <a href="https://chrisfountoulis.com">Chris Fountoulis</a> at <a href="https://growthofinfluence.com">Growth Of Influence</a>.</p>
