# Deploy to Environment

Ask the user the following two questions before doing anything:

**Q1. Branch to deploy:**
Run `git branch -a` and show the available branches.
Ask the user which branch to deploy. Suggest the current branch as the default.

**Q2. Target environment:**
Ask which environment:
- `staging` — deploy to staging for testing and validation
- `production` — deploy to production (requires explicit confirmation)

---

Once both answers are provided:

**If environment is `production`:**
Ask for explicit confirmation before proceeding:
> "You are about to deploy branch `{branch}` to **PRODUCTION**. Type `yes` to confirm."
Do not proceed until the user types `yes`.

**Trigger the GitHub Actions deploy workflow:**
```
gh workflow run deploy.yml \
  --ref {branch} \
  --field environment={environment}
```

**Check the workflow run status:**
```
gh run list --workflow=deploy.yml --limit=1
```

Show the user the workflow run URL and its current status.

**If the workflow fails**, fetch and display the failed step logs:
```
gh run view {run-id} --log-failed
```

Report the failure reason and suggest next steps.
