#!/usr/bin/env python3
"""Claude-powered PR review agent for Dark Factory."""
import json
import os
import sys
import time
import urllib.error
import urllib.request

import openai

MAX_DIFF_CHARS = 60_000

CODERABBIT_BOT = "coderabbitai[bot]"
CR_POLL_TIMEOUT = 480
CR_POLL_INTERVAL = 30

SYSTEM_PROMPT = """\
You are a senior code reviewer for Dark Factory — a stateless REST proxy for USGS \
Earthquake data, built with Python 3.13, FastAPI, and Clean Architecture.

Strict architecture rules:
- Four layers (strict inward dependency): domain → application → infrastructure → interface
- domain/ must have ZERO external imports (stdlib only)
- infrastructure implements domain ports; it is NEVER imported by application or domain
- EarthquakeFilter lives in value_objects.py; filters.py is a re-export shim only

Development best practices to enforce:
- TELL DON'T ASK: Objects should make decisions themselves. Flag code that queries an \
object's state to make an external decision (e.g., `if obj.status == X: obj.do()`) — \
this should instead be `obj.activate()`. Getters that expose internal state for \
decision-making are violations.
- Clean Code: Flag God objects (classes doing too much), meaningless names, functions \
longer than 20–30 lines with multiple responsibilities, comments that explain WHAT the \
code does instead of WHY, magic numbers/strings without named constants.
- TDD and test quality: Flag tests without Given/When/Then structure. Flag tests that \
mock internals or implementation details rather than testing observable behaviour. Flag \
tests without descriptive names. Flag test files missing edge-case coverage (None/empty \
inputs, error paths).
- Hexagonal Architecture compliance: Domain layer must be stdlib-only. Application layer \
must depend only on domain and ports (ABCs). Infrastructure must implement ports and \
never be imported by application/domain. Flag any direct infrastructure imports in \
application or domain.
- Exception coverage: Flag async endpoints that call external HTTP services but only \
catch httpx.HTTPStatusError without catching httpx.TransportError \
(ConnectError/TimeoutException). Missing TransportError causes 500 instead of 502.
- None-safe serialization: Flag GeoJSON coordinate construction like \
[eq.longitude, eq.latitude, eq.depth] when source model fields can be None.

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
- Use REQUEST_CHANGES for real bugs, architecture violations, security issues, severe \
TDA violations, clean code smells, or TDD anti-patterns.
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

### CI Checks
[✅/❌ result table from CI_SUMMARY, or "CI checks were not run." if empty]

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


def fetch_diff(repo: str, pr_number: str) -> tuple[str, bool]:
    """Return (diff_text, is_truncated). Truncated diffs must not be auto-approved."""
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
        suffix = "\n\n... [diff truncated — first 60k chars shown]"
        return diff[:MAX_DIFF_CHARS] + suffix, True
    return diff, False


def read_agents_md() -> str:
    try:
        with open("AGENTS.md") as f:
            return f.read()
    except OSError:
        return ""


def call_openai(
    pr_title: str, pr_body: str, diff: str, context: str, ci_summary: str
) -> dict:
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    ci_section = f"\n\n**CI Check Results:**\n{ci_summary}" if ci_summary else ""
    user_message = f"""\
Review this pull request.

**Title:** {pr_title}
**Description:** {pr_body or "(no description provided)"}

**Project Context (AGENTS.md):**
{context}
{ci_section}
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
        review_id = json.loads(body).get("id")
        print(f"Review posted without inline comments (id={review_id})")
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
        delimiter = "EOF_ISSUES"
        f.write(f"issues_json<<{delimiter}\n{issues_json}\n{delimiter}\n")


def wait_for_coderabbit(repo: str, pr_number: str) -> bool:
    """Poll for a CodeRabbit review every CR_POLL_INTERVAL seconds up to CR_POLL_TIMEOUT.

    Returns True if a CodeRabbit review is found, False if timed out.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews?per_page=100"
    deadline = time.monotonic() + CR_POLL_TIMEOUT
    while time.monotonic() < deadline:
        status, body = _github_request(url)
        if status == 200:
            reviews = json.loads(body)
            for review in reviews:
                if review.get("user", {}).get("login") == CODERABBIT_BOT:
                    print("CodeRabbit review found.")
                    return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sleep_secs = min(CR_POLL_INTERVAL, remaining)
        print(f"CodeRabbit review not yet found, waiting {sleep_secs:.0f}s...")
        time.sleep(sleep_secs)
    print("Timed out waiting for CodeRabbit review.")
    return False


def fetch_coderabbit_inline_comments(repo: str, pr_number: str) -> list:
    """Fetch inline PR comments from CodeRabbit.

    Returns a list of dicts with keys: file, line, description.
    """
    url = (
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments?per_page=100"
    )
    status, body = _github_request(url)
    if status != 200:
        print(f"Failed to fetch PR comments ({status})")
        return []
    comments = json.loads(body)
    result = []
    for comment in comments:
        if comment.get("user", {}).get("login") != CODERABBIT_BOT:
            continue
        file_path = comment.get("path", "")
        line = comment.get("line") or comment.get("original_line")
        raw_body = comment.get("body", "")
        description = f"[CodeRabbit] {raw_body}"[:400]
        result.append({"file": file_path, "line": line, "description": description})
    return result


def post_cr_label_comment(repo: str, pr_number: str, cr_issues: list) -> None:
    """Post an issue comment listing up to 10 CodeRabbit issues that will be auto-fixed."""
    shown = cr_issues[:10]
    lines = ["## 🐇 CodeRabbit Issues to Auto-Fix\n"]
    for issue in shown:
        file_ref = f"`{issue['file']}`" if issue.get("file") else "(unknown file)"
        line_ref = f" line {issue['line']}" if issue.get("line") else ""
        lines.append(f"- {file_ref}{line_ref}: {issue['description']}")
    if len(cr_issues) > 10:
        lines.append(f"\n_…and {len(cr_issues) - 10} more._")
    comment_body = "\n".join(lines)
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    status, _ = _github_request(url, method="POST", body={"body": comment_body})
    if status in (200, 201):
        print(f"CodeRabbit label comment posted ({len(shown)} issues listed).")
    else:
        print(f"Failed to post CodeRabbit label comment ({status})", file=sys.stderr)


def main() -> None:
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    pr_title = os.environ["PR_TITLE"]
    pr_body = os.environ.get("PR_BODY", "")
    head_sha = os.environ["HEAD_SHA"]
    ci_summary = os.environ.get("CI_SUMMARY", "")

    print(f"Reviewing PR #{pr_number}: {pr_title}")

    diff, is_truncated = fetch_diff(repo, pr_number)
    if not diff.strip():
        print("Empty diff — skipping review.")
        write_outputs(needs_fix=False, issues=[])
        return

    context = read_agents_md()
    review_data = call_openai(pr_title, pr_body, diff, context, ci_summary)

    decision = review_data.get("decision", "COMMENT")

    if is_truncated and decision == "APPROVE":
        print(
            "Diff was truncated — downgrading APPROVE to COMMENT;"
            " human review required."
        )
        review_data["decision"] = "COMMENT"
        decision = "COMMENT"
        truncation_notice = (
            "> ⚠️ **Diff truncated** — only the first 60 k characters were analysed."
            " Human review is required before approving.\n\n"
        )
        review_data["summary"] = truncation_notice + review_data.get("summary", "")

    issues = review_data.get("issues", [])

    post_review(repo, pr_number, head_sha, review_data)

    cr_issues: list = []
    cr_found = wait_for_coderabbit(repo, pr_number)
    if cr_found:
        cr_issues = fetch_coderabbit_inline_comments(repo, pr_number)
        post_cr_label_comment(repo, pr_number, cr_issues)

    all_issues = issues + cr_issues
    needs_fix = (decision == "REQUEST_CHANGES" and len(issues) > 0) or len(cr_issues) > 0

    print(
        f"Decision: {decision} | Claude issues: {len(issues)}"
        f" | CR issues: {len(cr_issues)} | Auto-fix: {needs_fix}"
    )
    write_outputs(needs_fix=needs_fix, issues=all_issues)


if __name__ == "__main__":
    main()
