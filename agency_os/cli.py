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
from . import stats as stats_mod
from .loops import open_loops
from .scaffold import ScaffoldError, init as scaffold_init
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


# -- init ---------------------------------------------------------------

def cmd_init(args):
    import os
    try:
        created = scaffold_init(args.target, args.name, vault_dir=args.vault_dir,
                                examples=not args.no_examples, force=args.force, hooks=args.hooks)
    except ScaffoldError as exc:
        raise UsageError(str(exc))
    paint = Painter()
    print(paint("agency-os init: {} is ready".format(args.name), "gold", "bold"))
    for path in created:
        rel = os.path.relpath(path)
        print("  created  {}".format(path if rel.startswith("..") else rel))
    vault = Vault(os.path.join(args.target, args.vault_dir))
    result = lint(vault)
    print("\n  {} notes, lint {}".format(len(vault.knowledge_notes()),
                                          "clean" if not result.findings else "{} findings".format(len(result.findings))))
    print("\nNext:")
    print("  1. Open {} in Obsidian (Open folder as vault).".format(os.path.join(args.target, args.vault_dir)))
    print("  2. Fill in the blanks in {}.".format(os.path.join(args.target, "CLAUDE.md")))
    print("  3. Start Claude Code in {} with the agency-os plugin enabled.".format(args.target))
    return EXIT_OK


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


# -- stats ---------------------------------------------------------------

def cmd_stats(args):
    vault = open_vault(args.vault)
    data = stats_mod.compute(vault)
    if args.format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(stats_mod.render(data, args.vault or vault.root))
    return EXIT_OK


# -- loops ---------------------------------------------------------------

def cmd_loops(args):
    vault = open_vault(args.vault)
    loops = open_loops(vault, today=args.today)
    if args.overdue:
        loops = [l for l in loops if l["overdue"]]
    if args.owner:
        loops = [l for l in loops if l.get("owner", "").lower() == args.owner.lower()]
    if args.format == "json":
        print(json.dumps(loops, indent=2, ensure_ascii=False))
        return EXIT_OK
    paint = Painter()
    if not loops:
        print("agency-os loops: nothing {}".format("overdue" if args.overdue else "open"))
        return EXIT_OK
    for l in sorted(loops, key=lambda x: (x.get("due") or "9999", x.get("loop", ""))):
        flag = paint("OVERDUE", "red", "bold") + " " if l["overdue"] else ""
        print("{}{}  {}  due {}  {}".format(flag, paint(l.get("loop", "?"), "bold"), l.get("owner", "-"),
                                          l.get("due", "-"), paint(l.get("where", ""), "dim")))
    overdue = sum(1 for l in loops if l["overdue"])
    print("\nagency-os loops: {} open, {} overdue".format(len(loops), overdue))
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(
        prog="agency-os",
        description="Run your agency on Claude Code and Obsidian: lint, index, log and spin out a shared vault.",
    )
    parser.add_argument("--version", action="version", version="agency-os " + __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("init", help="scaffold a vault, CLAUDE.md and vault-autopilot.md into a folder")
    p.add_argument("target", help="project folder to create or fill")
    p.add_argument("--name", default="Northwind Studio", help="your company name (default: the example agency)")
    p.add_argument("--vault-dir", default="vault", help="vault folder inside the target (default: vault)")
    p.add_argument("--no-examples", action="store_true", help="skip the fictional clients, projects and sessions")
    p.add_argument("--hooks", action="store_true",
                   help="also write .claude/settings.json hooks (for use without the plugin)")
    p.add_argument("--force", action="store_true", help="replace an existing vault folder and files")
    p.set_defaults(func=cmd_init)

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

    p = sub.add_parser("stats", help="note counts, link density, orphan rate, activity")
    p.add_argument("vault", nargs="?")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("loops", help="list open loops from the Open Loops Register")
    p.add_argument("vault", nargs="?")
    p.add_argument("--overdue", action="store_true", help="only loops past their due date")
    p.add_argument("--owner", help="only loops owned by this person")
    p.add_argument("--today", metavar="YYYY-MM-DD", help="evaluate due dates against this day")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=cmd_loops)

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
