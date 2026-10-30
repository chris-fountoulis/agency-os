"""Shared test helpers: paths, a temp-vault builder and a CLI runner."""

import contextlib
import io
import os
import shutil
import tempfile

from agency_os import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "template-vault")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def note(fields, body):
    """Render a note from a frontmatter dict and a body string."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            value = "[" + ", ".join(value) + "]"
        lines.append("{}: {}".format(key, value))
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.strip() + "\n"


class TempDir(object):
    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix="agency-os-test-")
        return self.path

    def __exit__(self, *exc):
        shutil.rmtree(self.path, ignore_errors=True)


def write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def copy_tree(src, dst):
    shutil.copytree(src, dst)
    return dst


def run_cli(*argv, stdin=None):
    """Run the CLI in-process; return (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    old_env = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "1"
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if stdin is not None:
                import sys
                saved = sys.stdin
                sys.stdin = io.StringIO(stdin)
                try:
                    code = cli.main(list(argv))
                finally:
                    sys.stdin = saved
            else:
                code = cli.main(list(argv))
    finally:
        if old_env is None:
            os.environ.pop("NO_COLOR", None)
        else:
            os.environ["NO_COLOR"] = old_env
    return code, out.getvalue(), err.getvalue()
