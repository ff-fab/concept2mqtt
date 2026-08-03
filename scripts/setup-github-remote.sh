#!/usr/bin/env bash
# Create the GitHub repository and push the initial scaffold via the gh CLI.
#
# Invoked automatically by copier's post-copy tasks when `create_remote_repo`
# is answered "yes". Safe to run again by hand: it skips creation when the repo
# or an "origin" remote already exists and just pushes 'main'.

set -euo pipefail

repo="ff-fab/concept2mqtt"
visibility="public"

# Capture the rendered description via a quoted heredoc so that any characters
# in it (double quotes, $, backticks) are treated literally instead of being
# re-quoted or expanded by the shell when passed to `gh repo create`.
description="$(cat <<'GH_REMOTE_DESCRIPTION_EOF'
Connect a concept2 rowing machine's PM5 to MQTT, e.g. for connection to a smart home.
GH_REMOTE_DESCRIPTION_EOF
)"

# 1. Preflight — gh must be installed and authenticated. If not, print how to
#    finish manually and exit 0 so scaffolding still succeeds.
if ! command -v gh >/dev/null 2>&1; then
    echo "⚠️  gh CLI not found — skipping remote setup."
    echo "    Install it from https://cli.github.com/ then run:"
    echo "    gh repo create ${repo} --${visibility} --source . --push"
    exit 0
fi
if ! gh auth status >/dev/null 2>&1; then
    echo "⚠️  gh CLI is not authenticated — skipping remote setup."
    echo "    Run 'gh auth login', then:"
    echo "    gh repo create ${repo} --${visibility} --source . --push"
    exit 0
fi

# 2. Ensure a git repo with at least one commit exists to push.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git init -b main >/dev/null 2>&1 || { git init >/dev/null && git checkout -b main; }
fi
if ! git rev-parse HEAD >/dev/null 2>&1; then
    # Ensure a committer identity exists before committing. Copier only sets
    # user.name/user.email when init_git_on_copy is enabled, so when the remote
    # flow runs on its own (or global git config is unset) the commit would
    # otherwise abort. Only set locally when not already configured.
    git config user.name  >/dev/null 2>&1 || git config user.name  "Fabian Koerner"
    git config user.email >/dev/null 2>&1 || git config user.email "mail@fabiankoerner.com"
    git add -A
    git commit -m "chore: initial scaffold from tmpl_python_project_kickstart" >/dev/null
fi

# 3. Idempotent: if an origin remote or the GitHub repo already exists, just push.
#    Guard against pushing the scaffold to an unrelated remote: only reuse an
#    existing "origin" when its URL actually points at the intended repo.
if git remote get-url origin >/dev/null 2>&1; then
    origin_url="$(git remote get-url origin)"
    case "${origin_url}" in
        *"github.com/${repo}" | *"github.com/${repo}.git" \
        | *"github.com:${repo}" | *"github.com:${repo}.git")
            echo "ℹ️  origin already points at ${repo} — pushing 'main'."
            git push -u origin main
            exit 0
            ;;
        *)
            echo "❌ An 'origin' remote already exists but points elsewhere:" >&2
            echo "     ${origin_url}" >&2
            echo "   Expected github.com/${repo}. Refusing to push the scaffold" >&2
            echo "   to an unexpected remote — fix 'origin' or push manually." >&2
            exit 1
            ;;
    esac
elif gh repo view "${repo}" >/dev/null 2>&1; then
    echo "ℹ️  ${repo} already exists on GitHub — adding origin and pushing 'main'."
    git remote add origin "https://github.com/${repo}.git"
    git push -u origin main
    exit 0
fi

# 4. Creating a repo is outward-facing — confirm when running interactively.
echo "📦 About to create ${visibility} repository ${repo} and push 'main'."
if [ -t 0 ]; then
    read -r -p "    Proceed? [y/N] " reply
    case "${reply}" in
        [yY] | [yY][eE][sS]) ;;
        *)
            echo "❌ Aborted — no remote created. Run this script again when ready:"
            echo "    bash scripts/setup-github-remote.sh"
            exit 0
            ;;
    esac
fi

# 5. Create the repo and push the scaffold.
gh repo create "${repo}" \
    --"${visibility}" \
    --source . \
    --remote origin \
    --push \
    --description "${description}"

echo "✅ Created ${repo} and pushed 'main'."
echo "🔗 https://github.com/${repo}"
