---
description: Runs the project standard verification suite (lint, test, format)
---

# Verification Skill

## Purpose
Run the standardized `make check` command to validate the current codebase state.

## Instructions
1.  Execute the shell command: `.\.cursor\skills\verification\scripts\run-check.ps1` (or `.sh` on Linux/Mac).
2.  Capture both STDOUT and STDERR.
3.  Analyze the output:
    - Look for "All checks passed!" -> Return status: PASS.
    - Look for "FAILED", "Error", or exit code != 0 -> Return status: FAIL with error details.

## Usage
- Call this whenever an implementation step is claimed to be done.
- Use this as the ground truth for the Verifier agent.