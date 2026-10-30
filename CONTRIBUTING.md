# Contributing

Thanks for helping. agency-os is small on purpose: a standard library CLI, a Claude Code plugin
and a template vault. Changes that keep it that way are the easiest to merge.

## Setup

```bash
git clone https://github.com/chris-fountoulis/agency-os
cd agency-os
python3 -m unittest discover -s tests        # Python 3.9 or newer, nothing to install
python3 scripts/agency-os lint template-vault --strict
```

To try the plugin from your checkout: `claude --plugin-dir /path/to/agency-os`.

## Before you open a pull request

- `python3 -m unittest discover -s tests` passes on Python 3.9.
- `python3 scripts/agency-os lint template-vault --strict` is clean and
  `python3 scripts/agency-os index template-vault --check` passes. If you touched notes, run
  `python3 scripts/agency-os index template-vault` and commit the result.
- Files added to `template-vault/` or `templates/` are listed under
  `[tool.setuptools.data-files]` in `pyproject.toml` (a test fails until they are).
- No runtime dependencies. The hooks run on every turn of every session on every teammate's
  machine; nothing to install is a feature.
- No em or en dashes in any file. A test enforces it.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/): `feat(lint): ...`,
  `fix(spinout): ...`, `docs: ...`, `test: ...`, `ci: ...`.

## Good first contributions

- A lint check you wish you had, with a fixture note that shows it firing.
- A credential shape `redact.py` misses (use made up values, built by concatenation in tests so
  secret scanners do not trip on them).
- A template your team uses that the template vault lacks.

## Changing the template vault

The template vault is documentation as much as data: it is the example every new team copies.
Keep the fictional agency consistent (Northwind Studio, its three clients, five people), tag
example content with `example` so `init --no-examples` can remove it, and make sure
`init --no-examples` still produces a lint-clean vault (a test checks).

## License

By contributing you agree that your contributions are licensed under the MIT License.
