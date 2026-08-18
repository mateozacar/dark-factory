#!/usr/bin/env python3
"""Claude-powered auto-fix agent for Dark Factory PRs."""
import json
import os
import subprocess
import sys
from collections import defaultdict

import openai

SYSTEM_PROMPT = """\
You are fixing code issues in the Dark Factory project — a stateless REST proxy for USGS \
Earthquake data, built with Python 3.13, FastAPI, and Clean Architecture.

Architecture rules:
- domain/ must have ZERO external imports (stdlib only)
- Dependency direction is strictly inward: interface → application → domain
- infrastructure implements domain ports and is NEVER imported by application or domain

You will receive a file path, its full current content, and a list of issues to fix.
Return ONLY the complete corrected file content — no explanations, no markdown fences, \
no "here is the fixed file" preamble. The output will be written directly to disk.
"""


def call_openai_fix(file_path: str, content: str, issues: list[dict]) -> str:
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    issue_list = "\n".join(
        f"- Line {i.get('line', '?')}: {i['description']}" for i in issues
    )
    user_message = f"""\
File: {file_path}

Issues to fix:
{issue_list}

Current file content:
```python
{content}
```

Return the complete fixed file content only."""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    fixed = response.choices[0].message.content.strip()
    # Strip accidental markdown fences
    if fixed.startswith("```"):
        lines = fixed.splitlines()
        end = -1 if lines[-1].strip() == "```" else len(lines)
        # Skip first line (```python or ```)
        fixed = "\n".join(lines[1:end])
    return fixed


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def main() -> None:
    issues_raw = os.environ.get("ISSUES_JSON", "[]")
    pr_branch = os.environ["PR_BRANCH"]
    pr_number = os.environ.get("PR_NUMBER", "?")

    try:
        all_issues: list[dict] = json.loads(issues_raw)
    except json.JSONDecodeError:
        print("Could not parse ISSUES_JSON — skipping auto-fix.", file=sys.stderr)
        sys.exit(0)

    if not all_issues:
        print("No issues to fix.")
        sys.exit(0)

    # Group issues by file
    by_file: dict[str, list[dict]] = defaultdict(list)
    for issue in all_issues:
        file_path = issue.get("file", "")
        if file_path:
            by_file[file_path].append(issue)

    fixed_files: list[str] = []

    for file_path, issues in by_file.items():
        if not os.path.isfile(file_path):
            print(f"Skipping {file_path} — not found on disk.")
            continue

        print(f"Fixing {file_path} ({len(issues)} issue(s))...")
        with open(file_path) as f:
            original = f.read()

        try:
            fixed = call_openai_fix(file_path, original, issues)
        except Exception as e:
            print(f"Claude failed for {file_path}: {e}", file=sys.stderr)
            continue

        if fixed == original:
            print(f"  No changes produced for {file_path}.")
            continue

        with open(file_path, "w") as f:
            f.write(fixed)
        fixed_files.append(file_path)
        print(f"  Fixed.")

    if not fixed_files:
        print("No files were changed — nothing to commit.")
        sys.exit(0)

    # Stage and commit
    run(["git", "add"] + fixed_files)

    issue_summary = "\n".join(
        f"- {i.get('file','?')}:{i.get('line','?')} {i['description']}"
        for i in all_issues
    )
    commit_msg = f"[ai-fix] resolve review findings (PR #{pr_number})\n\n{issue_summary}"

    result = run(["git", "commit", "-m", commit_msg], check=False)
    if result.returncode != 0:
        print(f"git commit failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Push to PR branch
    result = run(["git", "push", "origin", f"HEAD:{pr_branch}"], check=False)
    if result.returncode != 0:
        print(f"git push failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"Pushed auto-fix commit to {pr_branch} ({len(fixed_files)} file(s) changed).")


if __name__ == "__main__":
    main()
