#!/usr/bin/env bash
# Publish a finished build onto `main`, the branch Claude Code installs from.
#
#   scripts/publish-dist-to-main.sh <dist-dir> <version>
#
# Run from a checkout of the commit that was built, after
# `python -m build.build --set-version <version>` has filled <dist-dir>. The one
# path that writes built objects to `main`: publish-release.yml calls it for
# every tag (release candidates included), build-extension.yml for a merge into
# or a manual build of `main`.
#
# It commits onto the tip of origin/main, in a separate worktree, so the built
# source checkout is never what gets pushed:
#   - every built directory in <dist-dir> except `plugins` (the Antigravity
#     multi-plugin bundle) at the branch root, replaced whole: <plugin>-claude,
#     <plugin>-agy, and the rest;
#   - <dist-dir>/marketplace-production.json as .claude-plugin/marketplace.json;
#   - <dist-dir>/.aops-image-metadata.json, when the build wrote one;
#   - this checkout's auto-retarget-pr.yml, which fires only from the default
#     branch.
set -euo pipefail

DIST="$(realpath "${1:?usage: publish-dist-to-main.sh <dist-dir> <version>}")"
VERSION="${2:?usage: publish-dist-to-main.sh <dist-dir> <version>}"
SRC="$(git rev-parse --show-toplevel)"

[ -f "$DIST/marketplace-production.json" ] || {
    echo "::error::$DIST/marketplace-production.json missing: nothing to publish" >&2
    exit 1
}

WT="$(mktemp -d)"
git fetch --quiet origin main
git worktree add --quiet --detach "$WT" origin/main
trap 'git -C "$SRC" worktree remove --force "$WT"' EXIT
cd "$WT"

paths=()
for d in "$DIST"/*/; do
    name="$(basename "$d")"
    [ "$name" = plugins ] && continue
    rm -rf "$name"
    cp -a "$d" "$name"
    paths+=("$name")
done

mkdir -p .claude-plugin
cp "$DIST/marketplace-production.json" .claude-plugin/marketplace.json
paths+=(.claude-plugin/marketplace.json)

if [ -f "$DIST/.aops-image-metadata.json" ]; then
    cp "$DIST/.aops-image-metadata.json" .aops-image-metadata.json
    paths+=(.aops-image-metadata.json)
fi

if [ -f "$SRC/.github/workflows/auto-retarget-pr.yml" ]; then
    mkdir -p .github/workflows
    cp "$SRC/.github/workflows/auto-retarget-pr.yml" .github/workflows/auto-retarget-pr.yml
    paths+=(.github/workflows/auto-retarget-pr.yml)
fi

git add -f -A -- "${paths[@]}"
if git diff --cached --quiet; then
    echo "main already carries v$VERSION: nothing to publish"
    exit 0
fi
git -c user.name="github-actions[bot]" \
    -c user.email="github-actions[bot]@users.noreply.github.com" \
    commit --quiet --no-verify -m "chore: publish v$VERSION distribution to main [skip ci]"
git push origin HEAD:main
echo "Published v$VERSION to main ($(git rev-parse --short HEAD))"
