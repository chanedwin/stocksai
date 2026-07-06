"""PostToolUse hook: prose-lint any markdown file Claude writes or edits.

Reads the hook payload from stdin, runs scripts/check_prose.py on the file,
and exits 2 on violations so the agent sees and fixes them immediately.
"""

import json
import subprocess
import sys

payload = json.load(sys.stdin)
file_path = payload.get("tool_input", {}).get("file_path", "")
if not file_path.endswith(".md") or file_path.endswith("CLAUDE.md"):
    sys.exit(0)
result = subprocess.run(
    [sys.executable, "scripts/check_prose.py", file_path],
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print(result.stdout, file=sys.stderr)
    sys.exit(2)
