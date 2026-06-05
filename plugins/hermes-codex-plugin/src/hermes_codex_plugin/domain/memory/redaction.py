import re

PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    re.compile(
        r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+", re.I
    ),
    re.compile(r"\bAuthorization:\s*Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"\b[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{16,}\b"),
]


def redact(text: str) -> str:
    clean = text
    for pattern in PATTERNS:
        clean = pattern.sub("[REDACTED]", clean)
    return clean
