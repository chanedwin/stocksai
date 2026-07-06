"""Prose lint for CLAUDE.md section 4: no em dashes, no AI-ism vocabulary.

Scans markdown files under docs/ (and any paths passed as arguments).
Exits nonzero with file:line locations if a banned pattern appears.
Code blocks are skipped; CLAUDE.md itself is exempt (it defines the list).
"""

import re
import sys
from pathlib import Path

# Context-dependent terms from CLAUDE.md section 4.2 (leverage as a verb,
# comprehensive as praise, robust outside statistics, metaphorical
# landscape) are left to human review; only unambiguous bans are linted.
BANNED_WORDS = [
    "delve",
    "notably",
    "utilize",
    "furthermore",
    "moreover",
    "seamless",
    "cutting-edge",
    "multifaceted",
    "tapestry",
    "paradigm",
    "underscores",
    "underpin",
]

BANNED_PHRASES = [
    "it's worth noting",
    "it is worth noting",
    "in order to",
    "it is important to note",
    "plays a crucial role",
    "serves as a testament",
    "let's dive in",
    "at its core",
    "in the realm of",
]

EM_DASH = "—"

WORD_RE = re.compile(
    r"\b(" + "|".join(BANNED_WORDS) + r")\b", re.IGNORECASE
)
PHRASE_RE = re.compile(
    "|".join(re.escape(p) for p in BANNED_PHRASES), re.IGNORECASE
)


def check_file(path: Path) -> list[str]:
    problems = []
    in_code_block = False
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if EM_DASH in line:
            problems.append(f"{path}:{lineno}: em dash")
        m = WORD_RE.search(line)
        if m:
            problems.append(f"{path}:{lineno}: banned word '{m.group(0)}'")
        m = PHRASE_RE.search(line)
        if m:
            problems.append(f"{path}:{lineno}: banned phrase '{m.group(0)}'")
    return problems


def main() -> int:
    args = sys.argv[1:]
    if args:
        targets = [Path(a) for a in args if a.endswith(".md")]
    else:
        targets = sorted(Path("docs").rglob("*.md"))
    problems = []
    for path in targets:
        if path.name == "CLAUDE.md" or not path.exists():
            continue
        problems.extend(check_file(path))
    for p in problems:
        print(p)
    if problems:
        print(f"\n{len(problems)} prose violation(s). See CLAUDE.md section 4.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
