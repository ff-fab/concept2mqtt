````skill
---
name: pr-review
description:
  Evaluate PR findings, CI results, and reviewer comments. Use when reviewing a PR,
  when the user says "review this PR", "check the PR feedback", "what did reviewers
  say", or when preparing to address review comments. Fetches ALL feedback sources
  deterministically, then provides actionable analysis with teaching context.
---

# PR Review & Learning

Analyze the current pull request by first collecting ALL reviewer feedback
deterministically, then providing actionable analysis with educational context.

## Step 1: Fetch All PR Feedback (mandatory)

Run the feedback-collection script. This fetches every feedback source from GitHub in
one deterministic pass — PR metadata, changed files, reviews, inline review comments,
conversation comments, and CI status:

```bash
bash .github/skills/pr-review/fetch-pr-feedback.sh [PR_NUMBER]
```

If the user specified a PR number, pass it as the argument. Otherwise, omit it and the
script auto-detects the PR for the current branch.

**Do NOT skip this step.** Do NOT try to fetch PR data using other tools or ad-hoc `gh`
commands. The script handles pagination and fetches from all 5 GitHub API endpoints that
store review feedback. Running the script is the ONLY way to guarantee nothing is missed.

### What the script returns

A single JSON object with these keys:

| Key                      | What it contains                                         |
| ------------------------ | -------------------------------------------------------- |
| `metadata`               | PR title, body, state, labels, author                    |
| `changed_files`          | Every file changed with diff patches                     |
| `reviews`                | Top-level review submissions (approve/request-changes)   |
| `review_comments`        | **Inline comments on specific diff lines** (often missed)|
| `conversation_comments`  | General PR discussion (not attached to code lines)       |
| `ci_status`              | Commit statuses and check-run results                    |

> **Why this matters:** GitHub stores review feedback in 3 separate API resources.
> Agents routinely miss inline review comments (the most actionable feedback) because
> they only hit one endpoint. This script hits all of them.

## Step 2: Read Changed Files

For each file in the `changed_files` output, read the full current file content so you
can understand the diff in context. The patch in the JSON gives you the diff hunks, but
you need the full files to analyze patterns, architecture, and testability.

## Step 3: Analyze

### 3a. CI & Status Checks

- Identify failing checks and their root cause from `ci_status`
- Flag coverage regressions with specific modules affected
- Note any flaky test patterns

### 3b. Review Comments

Triage ALL comments — from `reviews`, `review_comments`, AND `conversation_comments` —
into categories:

- **Blocking** — must be resolved before merge
- **Suggestion** — improvement ideas, optional
- **Question** — needs a response/clarification

For each comment, propose a concrete fix or response.

**Pay special attention to `review_comments`** — these are inline findings attached to
specific lines of code. Group them by file and address each one.

### 3c. Code Quality Review

Review the diff for:

- **Correctness** — logic errors, edge cases, error handling
- **Style** — consistency with project conventions (see `.github/instructions/`)
- **Performance** — unnecessary allocations, N+1 patterns, blocking I/O
- **Security** — input validation, secrets exposure, injection risks
- **Testability** — missing test coverage, hard-to-test patterns

### 3d. Architecture & Design Teaching

For each significant finding, provide educational context:

1. **What it does** — brief factual description of the pattern or issue
2. **Why this approach** — the reasoning behind the recommendation
3. **Ecosystem context** — reference PEPs, RFCs, official docs by number
4. **Principle connections** — link to SOLID, DRY, GoF design patterns:
   - Name the pattern: Strategy, Factory, Observer, Adapter, etc.
   - Explain which SOLID principle applies (SRP, OCP, LSP, ISP, DIP)
   - Note if DRY/WET trade-offs are relevant
5. **Gotcha** — end with a common pitfall or "watch out for this"

### 3e. Language Idiom Spotting

Actively identify opportunities to use language idioms, even in correct code:

- **Python:** walrus operator, structural pattern matching, `itertools`, protocols vs
  ABCs, PEP references
- **TypeScript:** discriminated unions, `satisfies`, `const` assertions, branded types
- Explain _when_ the idiom helps and _when_ it hurts readability

## Step 4: Output

Structure the response as:

```markdown
## PR Summary

Brief description of what the PR does.

## Data Collection

- Files changed: N
- Reviews: N
- Inline review comments: N
- Conversation comments: N

## CI Status

- ✅ / ❌ status per check, with failure details

## Review Comments

### Blocking

- [file:line] Comment summary → Suggested fix + rationale

### Suggestions

- [file:line] Comment summary → Recommendation

### Questions

- Comment summary → Proposed response

## Code Quality Findings

### [Category: Correctness/Style/Performance/Security/Testability]

- [file:line] Finding → Fix + teaching moment

## Learning Moments

### [Pattern/Principle Name]

What → Why → Ecosystem → Principle → Gotcha

## Recommended Actions

1. Prioritized list of changes to make
2. Which can be batched vs need sequential work
```

## Interaction Notes

- Be specific: reference exact files and line numbers
- Propose concrete code changes, not vague suggestions
- Teaching should feel natural, not lecturing — weave it into the fix rationale
- If the code is already good, say so and explain _why_ it's good (reinforce learning)
- Acknowledge trade-offs when recommending changes
- If any section of the JSON output is empty, say so explicitly (e.g., "No inline
  review comments found.") — never silently skip a section

````
