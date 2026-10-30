"""Command line entry point: ``agency-os <command> [options]``.

Exit codes
  0  success (lint: no errors, or no findings at all with --strict)
  1  the command ran and found a problem (lint errors, spinout leak, ...)
  2  usage or configuration error (bad path, unreadable agency-os.json)
"""

import argparse
import json
import sys

from . import __version__
from .config import ConfigError
from . import index as index_mod
from .lint import CHECKS, lint
from .term import Painter
from .vault import Vault, find_vault

EXIT_OK, EXIT_FINDINGS, EXIT_USAGE = 0, 1, 2


class UsageError(Exception):
    pass


def open_vault(path):
    target = path
    if target is None:
        target = find_vault(".")
        if target is None:
            raise UsageError("no vault found here; pass a path or run inside a vault (a folder with agency-os.json)")
    try:
        return Vault(target)
    except FileNotFoundError as exc:
        raise UsageError(str(exc))


# -- lint ---------------------------------------------------------------

def cmd_lint(args):
    vault = open_vault(args.vault)
    ignore = set()
    for item in args.ignore or []:
        ignore.update(x.strip() for x in item.split(",") if x.strip())
    unknown = ignore - set(CHECKS)
    if unknown:
        raise UsageError("unknown check(s) for --ignore: {}".format(", ".join(sorted(unknown))))
    result = lint(vault, ignore=ignore)
    if args.format == "json":
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    else:
        paint = Painter()
        if not args.quiet:
            for f in result.findings:
                sev = paint("{:<7}".format(f.severity), "red" if f.severity == "error" else "yellow")
                print("{}  {}  {:<15}  {}".format(sev, paint(f.location(), "bold"), f.check, f.message))
            if result.findings:
                print()
        status = paint("clean", "green") if not result.findings else "{} {}, {} {}".format(
            len(result.errors), "error" if len(result.errors) == 1 else "errors",
            len(result.warnings), "warning" if len(result.warnings) == 1 else "warnings")
        print("agency-os lint: {} notes, {} links, {}".format(
            len(vault.knowledge_notes()), result.link_count(), status))
    if result.errors or (args.strict and result.findings):
        return EXIT_FINDINGS
    return EXIT_OK


# -- index --------------------------------------------------------------

def cmd_index(args):
    vault = open_vault(args.vault)
    rel = vault.config["index"]
    if args.check:
        if index_mod.is_current(vault):
            print("agency-os index: {} is up to date".format(rel))
            return EXIT_OK
        print("agency-os index: {} is stale; run `agency-os index`".format(rel))
        return EXIT_FINDINGS
    if args.stdout:
        sys.stdout.write(index_mod.render(vault))
        return EXIT_OK
    _, changed = index_mod.write_index(vault)
    count = len([n for n in vault.knowledge_notes() if n.rel != rel])
    print("agency-os index: {} {} ({} notes)".format(rel, "written" if changed else "unchanged", count))
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(
        prog="agency-os",
        description="Run your agency on Claude Code and Obsidian: lint, index, log and spin out a shared vault.",
    )
    parser.add_argument("--version", action="version", version="agency-os " + __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("lint", help="check vault integrity (links, orphans, hubs, frontmatter, names)")
    p.add_argument("vault", nargs="?", help="vault folder (default: nearest vault above the current folder)")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    p.add_argument("--quiet", "-q", action="store_true", help="print the summary line only")
    p.add_argument("--ignore", action="append", metavar="CHECK[,CHECK]",
                   help="skip checks: " + ", ".join(CHECKS))
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("index", help="regenerate the All Notes Index note")
    p.add_argument("vault", nargs="?")
    p.add_argument("--check", action="store_true", help="exit 1 if the index is stale, write nothing")
    p.add_argument("--stdout", action="store_true", help="print the index instead of writing it")
    p.set_defaults(func=cmd_index)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return args.func(args)
    except (UsageError, ConfigError) as exc:
        sys.stderr.write("agency-os: {}\n".format(exc))
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
