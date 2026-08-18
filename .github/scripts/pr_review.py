#!/usr/bin/env python3
"""Claude-powered PR review agent for Dark Factory."""
import json
import os
import sys
import urllib.request
import urllib.error

import openai

MAX_DIFF_CHARS = 60_000

SYSTEM_PROMPT = """\
You are a senior code reviewer for Dark Factory — a stateless REST proxy for USGS \
Earthquake data, built with Python 3.13, FastAPI, and Clean Architecture.

Strict architecture rules:
- Four layers (strict inward dependency): domain → application → infrastructure → interface
- domain/ must have ZERO external imports (stdlib only)
- infrastructure implements domain ports; it is NEVER imported by application or domain
- EarthquakeFilter lives in value_objects.py; filters.py is a re-export shim only

Return ONLY a valid JSON object with this exact structure (no markdown fences, no extra text):
{
  "decision": "APPROVE" | "REQUEST_CHANGES",
  "summary": "<full markdown review comment>",
  "issues": [
    {"file": "src/...", "line": <int>, "description": "<short description>"}
  ],
  "inline_comments": [
    {"path": "src/...", "line": <int>, "side": "RIGHT", "body": "<comment>"}
  ]
}

Rules:
- Use REQUEST_CHANGES only for real bugs, architecture violations, or security issues.
  Style nits and suggestions warrant APPROVE with comments.
- issues[] must list every item that justifies REQUEST_CHANGES. Empty list if APPROVE.
- inline_comments[] must only reference line numbers that appear as added lines (+) in \
the diff. If unsure of the exact line number, omit the inline comment and mention it in \
the summary instead.
- summary must be markdown using this template:

## 🤖 AI Code Review

### Summary
[1–3 sentences: what the PR does]

### Walkthrough
| File | Changes |
|------|---------|
| `path/to/file.py` | brief description |

### Issues Found
[bullet list, or "No issues found." if clean]

### Architecture Alignment
[✅/⚠️ bullets for each rule relevant to this diff]

---
*gpt-4o · Dark Factory PR Review*
"""


def _github_request(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    extra_headers: dict | None = None,
) -> tuple[int, str]:
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def fetch_diff(repo: str, pr_number: str) -> str:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        diff = resp.read().decode()
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n... [diff truncated — first 60k chars shown]"
    return diff


def read_agents_md() -> str:
    try:
        with open("AGENTS.md") as f:
            return f.read()
    except OSError:
        return ""


def call_openai(pr_title: str, pr_body: str, diff: str, context: str) -> dict:
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    user_message = f"""\
Review this pull request.

**Title:** {pr_title}
**Description:** {pr_body or "(no description provided)"}

**Project Context (AGENTS.md):**
{context}

**Diff:**
```diff
{diff}
```"""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def post_review(
    repo: str, pr_number: str, head_sha: str, review_data: dict
) -> None:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    payload = {
        "commit_id": head_sha,
        "body": review_data["summary"],
        "event": review_data["decision"],
        "comments": review_data.get("inline_comments", []),
    }

    status, body = _github_request(url, method="POST", body=payload)
    if status in (200, 201):
        review_id = json.loads(body).get("id")
        print(f"Review posted (id={review_id}, decision={review_data['decision']})")
        return

    # Retry without inline comments (common cause of 422)
    print(f"Review with inline comments failed ({status}), retrying without them...")
    payload.pop("comments")
    status, body = _github_request(url, method="POST", body=payload)
    if status in (200, 201):
        print(f"Review posted without inline comments (id={json.loads(body).get('id')})")
        return

    # Final fallback: plain issue comment
    print(f"Review API failed ({status}), falling back to plain comment...")
    comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    status2, _ = _github_request(
        comment_url, method="POST", body={"body": review_data["summary"]}
    )
    if status2 not in (200, 201):
        print(f"Plain comment also failed ({status2})", file=sys.stderr)
        sys.exit(1)
    print("Fallback plain comment posted.")


def write_outputs(needs_fix: bool, issues: list) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if not output_file:
        return
    issues_json = json.dumps(issues)
    with open(output_file, "a") as f:
        f.write(f"needs_fix={'true' if needs_fix else 'false'}\n")
        # Multiline value using heredoc syntax
        delimiter = "EOF_ISSUES"
        f.write(f"issues_json<<{delimiter}\n{issues_json}\n{delimiter}\n")


def main() -> None:
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    pr_title = os.environ["PR_TITLE"]
    pr_body = os.environ.get("PR_BODY", "")
    head_sha = os.environ["HEAD_SHA"]

    print(f"Reviewing PR #{pr_number}: {pr_title}")

    diff = fetch_diff(repo, pr_number)
    if not diff.strip():
        print("Empty diff — skipping review.")
        write_outputs(needs_fix=False, issues=[])
        return

    context = read_agents_md()
    review_data = call_openai(pr_title, pr_body, diff, context)

    decision = review_data.get("decision", "COMMENT")
    issues = review_data.get("issues", [])
    needs_fix = decision == "REQUEST_CHANGES" and len(issues) > 0

    print(f"Decision: {decision} | Issues: {len(issues)} | Auto-fix: {needs_fix}")

    post_review(repo, pr_number, head_sha, review_data)
    write_outputs(needs_fix=needs_fix, issues=issues)


if __name__ == "__main__":
    main()
