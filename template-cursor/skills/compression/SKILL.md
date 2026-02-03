# Compression Skill

## Purpose
Externalize working memory to files to prevent long-context degradation.

## When to run
- After each task is accepted (i.e., after `make check` passes).
- Or whenever the conversation feels long/drifty (manual trigger).

## Instructions
1) Create or update `SUMMARY.md` at repo root.
2) Append a new section with:
   - Task ID / Task title
   - What changed (high-level)
   - Key decisions / constraints
   - Public interfaces/contracts touched (function signatures, CLI, API, config)
   - Files changed (list)
   - Verification evidence (exact command + key output, e.g. `make check` and "All checks passed!")
3) Output ONLY:
   - A short pointer: "SUMMARY.md updated."
   - A recommendation whether to start a new chat and what files to @reference.

## Output format (strict)
- `summary_updated`: true/false
- `start_new_chat`: true/false
- `reference_next_chat`: [list of file paths]