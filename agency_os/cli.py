"""Command line entry point: ``agency-os <command> [options]``.

Exit codes
  0  success (lint: no errors, or no findings at all with --strict)
  1  the command ran and found a problem (lint errors, spinout leak, ...)
  2  usage or configuration error (bad path, unreadable agency-os.json)
"""

import argparse
import json
import os
import sys

from . import __version__
from .config import ConfigError
from . import index as index_mod
from . import stats as stats_mod
from .loops import open_loops
from . import sessions
from .spinout import SpinoutError, spinout as do_spinout
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
    print("\n  {} notes, lint {}".format(result.note_count(),
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
    elif args.format == "github":
        # GitHub Actions workflow commands: findings show up as annotations on the files.
        prefix = os.path.relpath(vault.root) if args.vault else ""
        for f in result.findings:
            path = os.path.join(prefix, f.note).replace(os.sep, "/") if prefix not in ("", ".") else f.note
            level = "error" if f.severity == "error" else "warning"
            line = ",line={}".format(f.line) if f.line else ""
            msg = f.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print("::{} file={}{},title=agency-os {}::{}".format(level, path, line, f.check, msg))
        print("agency-os lint: {} notes, {} errors, {} warnings".format(
            result.note_count(), len(result.errors), len(result.warnings)))
    else:
        paint = Painter()
        if not args.quiet:
            current = None
            for f in result.findings:
                if f.note != current:
                    if current is not None:
                        print()
                    print(paint(f.note, "bold"))
                    current = f.note
                sev = paint("{:<7}".format(f.severity), "red" if f.severity == "error" else "yellow")
                print("  {:>4}  {}  {:<15}  {}".format(f.line or "", sev, f.check, f.message))
            if result.findings:
                print()
        status = paint("clean", "green") if not result.findings else "{} {}, {} {}".format(
            len(result.errors), "error" if len(result.errors) == 1 else "errors",
            len(result.warnings), "warning" if len(result.warnings) == 1 else "warnings")
        print("agency-os lint: {} notes, {} links, {}".format(result.note_count(), result.link_count(), status))
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


# -- hooks: session-log, checkpoint, context ------------------------------

def _hook(args, handler):
    """Run a hook handler. Hooks never block Claude Code: failures go to stderr, exit 0."""
    payload = sessions.read_payload(sys.stdin)
    try:
        root = sessions.locate_vault(args.vault, payload)
        if root is None:
            return EXIT_OK
        path = handler(payload, root)
        if path and args.verbose:
            sys.stderr.write("agency-os: wrote {}\n".format(path))
    except Exception as exc:  # noqa: BLE001 - a hook must not crash the session
        sys.stderr.write("agency-os {}: {}\n".format(args.command, exc))
    return EXIT_OK


def cmd_session_log(args):
    return _hook(args, lambda payload, root: sessions.session_log(payload, root, person=args.person))


def cmd_checkpoint(args):
    return _hook(args, lambda payload, root: sessions.checkpoint(payload, root, person=args.person))


def cmd_context(args):
    payload = sessions.read_payload(sys.stdin) if args.hook else {}
    try:
        root = sessions.locate_vault(args.vault, payload)
        if root is None:
            if not args.hook:
                raise UsageError("no vault found; pass a path")
            return EXIT_OK
        project = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        print(sessions.context(root, project_dir=project, today=args.today))
    except UsageError:
        raise
    except Exception as exc:  # noqa: BLE001
        if not args.hook:
            raise
        sys.stderr.write("agency-os context: {}\n".format(exc))
    return EXIT_OK


# -- spinout -------------------------------------------------------------

def cmd_spinout(args):
    if not args.vault:
        raise UsageError("spinout needs the source vault path")
    try:
        report = do_spinout(args.vault, args.client, args.out, denylist_files=args.denylist or (),
                            deny=args.deny or (), depth=args.depth, force=args.force)
    except (SpinoutError, OSError) as exc:
        raise UsageError(str(exc))
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        paint = Painter()
        print(paint("agency-os spinout: {} -> {}".format(report["client"], args.out), "gold", "bold"))
        print("\n  {} of {} notes selected:".format(len(report["notes"]), report["notes_in_source"]))
        for rel in report["notes"]:
            print("    " + rel)
        print("\n  links to notes left behind, unlinked: {}".format(report["links_unlinked"]))
        print("  notes with credentials redacted:     {}".format(report["notes_with_secrets_redacted"]))
        print("  denylist rules: {} ({} replacements)".format(
            len(report["terms"]), sum(t["replacements"] for t in report["terms"])))
        for t in report["terms"]:
            if t["replacements"]:
                print("    {:<8} {:<14} {:>3}x  {}".format(t["rule"], t["source"], t["replacements"], t["term"]))
        if report["leak_details"]:
            print(paint("\n  LEAKS: {}".format(len(report["leak_details"])), "red", "bold"))
            for rel, problem in report["leak_details"]:
                print("    {}  {}".format(rel, problem))
        else:
            print(paint("\n  verified: no denylisted term or credential shape left in the output", "green"))
        print("  report: {}".format(os.path.join(args.out, ".agency-os", "spinout-report.json")))
    return EXIT_FINDINGS if report["leak_details"] else EXIT_OK


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
    p.add_argument("--format", choices=("text", "json", "github"), default="text",
                   help="github prints GitHub Actions annotations")
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

    p = sub.add_parser("spinout", help="copy one client's notes and linked knowledge into a sanitised vault")
    p.add_argument("vault", help="source vault")
    p.add_argument("--client", required=True, help="client note name, e.g. \"Acme Bakery\"")
    p.add_argument("--out", required=True, help="folder for the new vault (must be outside the source)")
    p.add_argument("--denylist", action="append", metavar="FILE", help="file with one term per line to scrub")
    p.add_argument("--deny", action="append", metavar="TERM", help="extra term to scrub (repeatable)")
    p.add_argument("--depth", type=int, default=1, help="levels of linked knowledge to follow (default 1)")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--force", action="store_true", help="replace a non-empty output folder")
    p.set_defaults(func=cmd_spinout)

    hook_help = "reads the Claude Code hook JSON on stdin; always exits 0"
    p = sub.add_parser("session-log", help="append a session log entry from a Stop hook payload on stdin",
                       description="Append a structured session log entry. " + hook_help)
    p.add_argument("--vault", help="vault folder (default: found from the payload cwd)")
    p.add_argument("--person", help="name for the log file (default: git user.name)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(func=cmd_session_log)

    p = sub.add_parser("checkpoint", help="save a checkpoint note from a PreCompact hook payload on stdin",
                       description="Save a checkpoint note before compaction. " + hook_help)
    p.add_argument("--vault")
    p.add_argument("--person")
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("context", help="print the session-start briefing: vault, open loops, recent sessions")
    p.add_argument("vault", nargs="?")
    p.add_argument("--hook", action="store_true", help="read the SessionStart payload on stdin, stay silent without a vault")
    p.add_argument("--today", metavar="YYYY-MM-DD")
    p.set_defaults(func=cmd_context)

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
