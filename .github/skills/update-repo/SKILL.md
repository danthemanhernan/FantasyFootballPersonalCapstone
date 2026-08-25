---
name: update-repo
description: "Use when: creating a feature branch, committing changes, pushing to GitHub, and opening a pull request. Streamlines the process of updating a repository with version-specific branch names and comprehensive commit messages. Handles single or multi-version updates (e.g., v2, v2-v3) in branch names and notes."
---

# Update Repo Skill

A workflow for streamlined repository updates: branch creation, change commits, remote push, and PR opening.

## Triggers

Use this skill when you want to:
- Create a feature branch with version-based naming (e.g., `v2/persistence`, `v3-v4/feature`)
- Stage and commit all current changes with a descriptive message
- Push the branch to GitHub
- Open a pull request with full context

## Workflow Steps

### 1. Gather Information

Ask the user for:
- **Feature name/description** (e.g., "local persistence", "event schema refactor")
- **Version(s)** being updated (single: "v2", or range: "v2-v3")
- **Base branch** (default: "main")
- **Commit message details** (auto-generate from feature + versions, allow customization)

### 2. Create Branch

```bash
git checkout -b v{VERSION}/{feature-name}
# Examples:
# git checkout -b v2/persistence
# git checkout -b v2-v3/event-schema
```

**Multi-version naming**: If updating from v2 to v3, use `v2-v3/` prefix to signal the span.

### 3. Commit Changes

```bash
git add -A
git commit -m "V{VERSION}: {Title}

{Detailed bullet points of changes}

Files changed:
- file1 (new|updated)
- file2 (new|updated)

{Optional: Link to design docs or ADRs}"
```

**Multi-version format**:
```
V{START}-V{END}: {Title}
```

Example:
```
V2-V3: Add persistence and event schema updates

- Implement V2 local storage layer
- Update V3 event contract with new fields
- Migrate legacy event handling
- Add compatibility tests
```

### 4. Push Branch

```bash
git push -u origin v{VERSION}/{feature-name}
```

If network auth fails, suggest:
1. Verify `gh auth status` shows logged-in state
2. Try SSH: `git remote set-url origin git@github.com:owner/repo.git`
3. Use GitHub CLI: `gh pr create ...`

### 5. Open Pull Request

**Option A: Using GitHub CLI** (recommended if push succeeds)
```bash
gh pr create --title "{Title}" --body "{PR body}" --base main --head v{VERSION}/{feature-name}
```

**Option B: Manual**
Direct user to GitHub UI: `https://github.com/{owner}/{repo}/compare/main...v{VERSION}/{feature-name}`

## PR Template

```markdown
# {Feature Title}

**Version(s)**: v{VERSION} [or v{START}-v{END} for multi-version]

## Changes
- Bullet 1
- Bullet 2
- Bullet 3

## Files Changed
- path/file1 (new|updated)
- path/file2 (new|updated)

## Design & Rationale
{Link to design docs, ADRs, or curriculum versions}

{Optional test results, migration notes, breaking changes}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No commits between main and branch" | Verify the branch has local commits via `git log origin/main..HEAD` |
| Network 403 error on push | Use `gh auth status` to verify authentication; try SSH remote |
| PR creation fails | Ensure branch is pushed first; use GitHub CLI (`gh pr create`) for better error messages |
| Want to abort | Use `git checkout main && git branch -D v{VERSION}/{feature-name}` |

## Notes

- **Branch naming** encodes the version in the path to make the version history scannable in GitHub UI.
- **Multi-version commits** should include notes about what changed *between* versions (migrations, breaking changes) so future PRs can reference the boundary.
- **Commit message detail** matters: future you will need to know why changes were made at each version boundary.
- After the workflow, verify tests pass and review the PR details before merging.
