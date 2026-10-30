"""Credential redaction for anything a hook writes into the vault.

Session logs quote prompts and replies, and people paste secrets into prompts.
Every string is passed through ``redact`` before it touches disk. The rules
favour false positives: a redacted hash in a log costs nothing, a leaked
token in a shared vault costs a rotation.
"""

import re

# "password: X", "token=X", "api key is X": the value goes when it looks like a credential.
KEYWORD = re.compile(
    r"(?i)(?<![A-Za-z])(pass(?:word|wd|phrase)?|secret|token|api[_ -]?key|access[_-]?key|"
    r"private[_-]?key|client[_-]?secret|auth[_-]?token)\b(\s*[:=]\s*|\s+is\s+)([^\s\"'<>\[\]]+)"
)

PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED-PRIVATE-KEY]"),
    (re.compile(r"(?i)\b(authorization\s*:\s*(?:basic|bearer|token)?)\s*\S{8,}"), r"\1 [REDACTED]"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}"), "[REDACTED-KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"), "[REDACTED-KEY]"),
    (re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}"), "[REDACTED-KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED-GITHUB-TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[REDACTED-GITHUB-TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED-AWS-KEY]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "[REDACTED-SLACK-TOKEN]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "[REDACTED-GOOGLE-KEY]"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[REDACTED-JWT]"),
    (re.compile(r"(?i)(https?://)[^\s/:@]+:[^\s/@]+@"), r"\1[REDACTED]@"),
    (re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])"), "[REDACTED-HEX]"),
    # Long opaque strings; "/" is excluded so file paths survive.
    (re.compile(r"(?<![A-Za-z0-9+_\-])[A-Za-z0-9+_\-]{40,}={0,2}(?![A-Za-z0-9+_\-])"), "[REDACTED-LONG-STRING]"),
)

# The same shapes as one expression, for scanners (sync, spinout) that only need yes or no.
SECRET_SHAPES = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]{16,}|sk-[A-Za-z0-9_\-]{20,}|(?:sk|rk)_live_[A-Za-z0-9]{16,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY|xox[abprs]-[A-Za-z0-9\-]{10,}|AIza[0-9A-Za-z_\-]{35})"
)


def _looks_secret(value):
    v = value.rstrip(".,;:!?)\"'")
    if len(v) < 8:
        return False
    return bool(re.search(r"\d|[!@#$%^&*_+=/\\|~`]", v) or re.search(r"[a-z][^A-Z]*[A-Z]", v))


def redact(text):
    if not text:
        return text
    text = KEYWORD.sub(lambda m: m.group(1) + m.group(2) + ("[REDACTED]" if _looks_secret(m.group(3)) else m.group(3)), text)
    for rx, repl in PATTERNS:
        text = rx.sub(repl, text)
    return text


def has_secret(text):
    return bool(SECRET_SHAPES.search(text or ""))
