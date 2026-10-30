# FAQ

### Is this a second brain template?

It is a company brain. Personal second-brain setups optimise for one person's thinking. An
agency needs the opposite: one memory that five people and every Claude Code session share,
with rules about what goes where, who wrote what, and what must never leave the building. The
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

The SessionStart briefing parses and lints the vault once. A vault of a few hundred notes takes
well under a second. The production vault this was extracted from (about 900 notes) takes a few seconds, most of it reading files. The Stop hook reads the tail of the transcript (at most 4 MB) and
appends a few lines. Every hook has a timeout and exits 0 on any error.

### What if a session writes a broken link or forgets frontmatter?

That is what lint is for. The capture skill ends with a lint run, the SessionStart briefing
reports the lint state, and CI can block a push with errors. Session logs themselves cannot break
lint: unresolvable links in them are written as plain text.

### Can it leak secrets into git?

Three layers stand in the way: the session logger redacts credential shapes before writing, the
sync holds back any file whose new lines look like a credential, and the protocol tells sessions
to record where a credential lives, never its value. None of them is a substitute for not pasting
secrets into prompts.

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

Yes: `agency-os spinout`. See [client-vaults.md](client-vaults.md).

### Does it work on Windows?

The CLI and hooks are pure Python and run anywhere Python 3.9+ runs. The plugin's hook commands
call `python3`; on Windows, where the launcher is often `python` or `py`, use
`agency-os init --hooks` and edit the command in `.claude/settings.json`. The sync script needs
bash and git (Git Bash works); the background job templates are for macOS and Linux.

### How big can a vault get?

The production vault this was extracted from is about 900 notes across several merged sub-vaults
and lints in a few seconds, most of it disk reads. Link resolution is a dictionary lookup, so
nothing here is quadratic in the number of notes.
