#!/usr/bin/env python3
"""Enable auto-merge on a PR via GitHub REST/GraphQL API."""
import json
import os
import sys
import urllib.error
import urllib.request

CODERABBIT_BOT = "coderabbitai[bot]"


def github_request(
    url: str,
    method: str = "GET",
    body: dict | None = None,
) -> tuple[int, dict | list]:
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def graphql_request(query: str, variables: dict) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"errors": [{"message": exc.read().decode()}]}


def get_pr_node_id(repo: str, pr_number: str) -> str:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    status, data = github_request(url)
    if status != 200:
        print(f"Failed to fetch PR: {status} {data}", file=sys.stderr)
        sys.exit(1)
    return data["node_id"]  # type: ignore[index]


def enable_auto_merge(node_id: str) -> None:
    mutation = """
    mutation EnableAutoMerge($pullRequestId: ID!) {
      enablePullRequestAutoMerge(input: {
        pullRequestId: $pullRequestId,
        mergeMethod: SQUASH
      }) {
        pullRequest {
          autoMergeRequest {
            enabledAt
          }
        }
      }
    }
    """
    result = graphql_request(mutation, {"pullRequestId": node_id})
    if "errors" in result:
        errs = result["errors"]
        # If auto-merge is already enabled, treat as success
        if any("already enabled" in str(e).lower() for e in errs):
            print("Auto-merge already enabled.")
            return
        print(f"GraphQL error enabling auto-merge: {errs}", file=sys.stderr)
        sys.exit(1)


def post_comment(repo: str, pr_number: str, body: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    status, _ = github_request(url, method="POST", body={"body": body})
    if status not in (200, 201):
        print(f"Warning: could not post comment (HTTP {status})", file=sys.stderr)


def get_coderabbit_review_state(repo: str, pr_number: str) -> str | None:
    """Return the latest CodeRabbit review state, or None if not submitted yet."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews?per_page=100"
    status, data = github_request(url)
    if status != 200 or not isinstance(data, list):
        return None
    cr_reviews = [r for r in data if r.get("user", {}).get("login") == CODERABBIT_BOT]
    if not cr_reviews:
        return None
    latest = max(cr_reviews, key=lambda r: r.get("submitted_at", ""))
    return latest["state"]  # APPROVED | CHANGES_REQUESTED | COMMENTED | DISMISSED


def check_coderabbit_state(repo: str, pr_number: str) -> str | None:
    """Check the current CodeRabbit review state once and print the result."""
    state = get_coderabbit_review_state(repo, pr_number)
    if state is not None:
        print(f"CodeRabbit review state: {state}")
    else:
        print("No CodeRabbit review found.")
    return state


def main() -> None:
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    needs_fix = os.environ.get("NEEDS_FIX", "false")

    if needs_fix == "false":
        reason = "Review approved — no issues found."
    else:
        reason = "Auto-fix applied — remaining suggestions are non-blocking."

    cr_state = check_coderabbit_state(repo, pr_number)
    cr_note = f" CodeRabbit: `{cr_state}`." if cr_state else " CodeRabbit did not respond in time."

    node_id = get_pr_node_id(repo, pr_number)
    enable_auto_merge(node_id)
    post_comment(repo, pr_number, f"🤖 **Auto-merge enabled.** {reason}{cr_note}")
    print(f"Auto-merge enabled. Reason: {reason}")


if __name__ == "__main__":
    main()
