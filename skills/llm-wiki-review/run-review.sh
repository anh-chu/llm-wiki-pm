#!/usr/bin/env bash
# run-review.sh DRAFT [REVIEWER] — run the configured reviewer on a draft, print the review.
#
# REVIEWER: claude (default model), claude:haiku|sonnet|opus, codex, or any shell
# command that reads the prompt on stdin and prints the review. Order: argument
# (unless it is an unsubstituted ${...}) > WIKI_REVIEWER > claude.
# Claude reviewers run as a separate read-only `claude -p` in the wiki directory,
# with WIKI_REVIEW_RUNNING=1 so the review-gate hook does not gate the reviewer.
# Exits non-zero with a message on stderr when the review fails or is empty.
set -uo pipefail

draft="${1:?usage: run-review.sh DRAFT [REVIEWER]}"
reviewer="${2:-}"
case "$reviewer" in '${'*) reviewer= ;; esac
reviewer="${reviewer:-${WIKI_REVIEWER:-claude}}"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
wiki=$(sh "$here/../../hooks/resolve-wiki.sh")
[ -n "$wiki" ] && [ -d "$wiki" ] || { echo "run-review: no wiki configured" >&2; exit 2; }
[ -s "$draft" ] || { echo "run-review: draft $draft is missing or empty" >&2; exit 2; }

prompt=$(mktemp /tmp/wiki-review-prompt.XXXXXX)
out=$(mktemp /tmp/wiki-review-out.XXXXXX)
trap 'rm -f "$prompt" "$out"' EXIT
sed -e "s#{{WIKI}}#$wiki#g" -e "s#{{DRAFT}}#$draft#g" "$here/reviewer-prompt.md" > "$prompt"

case "$reviewer" in
  claude|claude:*)
    model_args=()
    [ "$reviewer" != claude ] && model_args=(--model "${reviewer#claude:}")
    (cd "$wiki" && WIKI_REVIEW_RUNNING=1 claude -p "${model_args[@]}" --setting-sources project --disable-slash-commands \
       --allowedTools "Read,Grep,Glob" < "$prompt" > "$out")
    ;;
  codex)
    codex exec --sandbox read-only --skip-git-repo-check --ephemeral -C "$wiki" -o "$out" \
      "$(cat "$prompt")" < /dev/null > /dev/null 2>&1
    ;;
  *)
    (cd "$wiki" && WIKI_REVIEW_RUNNING=1 sh -c "$reviewer" < "$prompt" > "$out")
    ;;
esac
status=$?

if [ $status -ne 0 ] || [ ! -s "$out" ]; then
  echo "run-review: reviewer '$reviewer' failed (exit $status, $(wc -c < "$out") bytes)" >&2
  exit 1
fi
echo "Reviewer: $reviewer"
cat "$out"
