import argparse
import datetime as _dt
import os
import re
from dataclasses import dataclass

BAR_WIDTH = 20


def now_local_str() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def progress_bar(done: int, total: int) -> str:
    if total <= 0:
        filled = 0
    else:
        filled = round(BAR_WIDTH * (done / total))
    filled = max(0, min(BAR_WIDTH, filled))
    return "[" + ("#" * filled) + ("-" * (BAR_WIDTH - filled)) + "]"


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def replace_line(text: str, pattern: str, replacement: str) -> str:
    # Replace first matching line (multiline).
    return re.sub(pattern, replacement, text, count=1, flags=re.MULTILINE)


@dataclass
class TaskRow:
    index: int
    task_id: str
    desc: str
    risk: str
    status: str
    updated_at: str
    evidence: str


def parse_tasks_table_rows(progress_md: str) -> list[TaskRow]:
    """
    Parse rows from the '子任务清单（PR 粒度）' markdown table.
    Expects row format:
    | 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |
    """
    rows: list[TaskRow] = []
    in_table = False
    for line in progress_md.splitlines():
        if line.strip() == "## 子任务清单（PR 粒度）":
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table:
            continue
        if not line.startswith("|"):
            continue
        if line.startswith("|---"):
            continue
        if "序号" in line and "Task ID" in line:
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) != 7:
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            continue
        rows.append(
            TaskRow(
                index=idx,
                task_id=parts[1],
                desc=parts[2],
                risk=parts[3],
                status=parts[4],
                updated_at=parts[5],
                evidence=parts[6],
            )
        )
    return rows


def render_tasks_table(rows: list[TaskRow]) -> str:
    lines = []
    lines.append("| 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: x.index):
        lines.append(
            f"| {r.index} | {r.task_id} | {r.desc} | {r.risk} | {r.status} | "
            f"{r.updated_at} | {r.evidence} |"
        )
    return "\n".join(lines) + "\n"


def upsert_task(
    progress_md: str, task_id: str, desc: str, risk: str, status: str, evidence: str
) -> str:
    rows = parse_tasks_table_rows(progress_md)
    updated_at = now_local_str()

    existing = next((r for r in rows if r.task_id == task_id), None)
    if existing:
        existing.desc = desc or existing.desc
        existing.risk = risk or existing.risk
        existing.status = status or existing.status
        existing.updated_at = updated_at
        if evidence:
            existing.evidence = evidence
    else:
        next_idx = (max((r.index for r in rows), default=0) + 1) if rows else 1
        rows.append(
            TaskRow(
                index=next_idx,
                task_id=task_id,
                desc=desc,
                risk=risk,
                status=status,
                updated_at=updated_at,
                evidence=evidence,
            )
        )

    table_text = render_tasks_table(rows)
    return replace_tasks_table(progress_md, table_text)


def replace_tasks_table(progress_md: str, new_table: str) -> str:
    # Replace the whole tasks table block (from header row to before next heading).
    pattern = r"(?ms)^## 子任务清单（PR 粒度）\s*\n.*?\n(?=^## )"
    replacement = "## 子任务清单（PR 粒度）\n\n" + new_table + "\n"
    if re.search(pattern, progress_md):
        return re.sub(pattern, replacement, progress_md, count=1)
    # If missing, append it before timeline.
    if "## 时间线（实时日志）" in progress_md:
        return progress_md.replace(
            "## 时间线（实时日志）", replacement + "## 时间线（实时日志）", 1
        )
    return progress_md + "\n" + replacement


def append_timeline_event(
    progress_md: str, subagent: str, phase: str, what: str, result: str, next_step: str
) -> str:
    ts = now_local_str()
    row = f"| {ts} | {subagent} | {phase} | {what} | {result} | {next_step} |"

    if "## 时间线（实时日志）" not in progress_md:
        progress_md += (
            "\n## 时间线（实时日志）\n\n"
            "| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 做了什么 | 结果/证据 | 下一步 |\n"
            "|---|---|---|---|---|---|\n"
        )

    # Append after the table header.
    lines = progress_md.splitlines()
    out = []
    in_tl = False
    header_seen = 0
    inserted = False
    for line in lines:
        out.append(line)
        if line.strip() == "## 时间线（实时日志）":
            in_tl = True
            continue
        if in_tl and line.startswith("|"):
            # header line + delimiter line
            header_seen += 1
            if header_seen == 2 and not inserted:
                out.append(row)
                inserted = True
            continue
        if in_tl and not line.startswith("|") and inserted:
            # table ended
            in_tl = False
    if not inserted:
        out.append(row)
    return "\n".join(out) + ("\n" if progress_md.endswith("\n") else "")


def append_summary_event(
    summary_md: str, subagent: str, phase: str, event: str, result: str, next_step: str
) -> str:
    ts = now_local_str()
    row = f"| {ts} | {subagent} | {phase} | {event} | {result} | {next_step} |"
    if "| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 事件 | 结果 | 下一步 |" not in summary_md:
        # Fallback minimal table
        summary_md = (
            "# SUMMARY\n\n"
            "> 大任务运行摘要（本次运行 append-only）\n\n"
            "## 运行日志（按时间追加）\n\n"
            "| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 事件 | 结果 | 下一步 |\n"
            "|---|---|---|---|---|---|\n"
        )
    return summary_md.rstrip("\n") + "\n" + row + "\n"


def recompute_overview(progress_md: str) -> str:
    rows = parse_tasks_table_rows(progress_md)
    total = len(rows)
    done = sum(1 for r in rows if r.status.strip().upper() == "PASS")
    percent = 0 if total == 0 else int(round(100 * done / total))
    bar = progress_bar(done, total)
    ts = now_local_str()

    progress_md = replace_line(
        progress_md,
        r"^- \*\*当前时间\*\*：.*$",
        f"- **当前时间**：{ts}",
    )
    progress_md = replace_line(
        progress_md,
        r"^- \*\*总进度\*\*：.*$",
        f"- **总进度**：{done}/{total}（{percent}%） {bar}",
    )
    return progress_md


def repo_root_from_script() -> str:
    # .cursor/scripts/progress_tools.py -> repo root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update PROGRESS.md and SUMMARY.md (Chinese, timestamped)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_event = sub.add_parser("event", help="Append an event to PROGRESS timeline and SUMMARY log.")
    p_event.add_argument(
        "--subagent",
        required=True,
        choices=["orchestrator", "planner", "implementers", "verifier", "skill", "system"],
    )
    p_event.add_argument("--phase", required=True, help="plan/implement/verify/fix/other")
    p_event.add_argument("--what", required=True, help="做了什么（简体中文）")
    p_event.add_argument("--result", default="", help="结果/证据（简体中文/短）")
    p_event.add_argument("--next", default="", help="下一步（简体中文/短）")

    p_task = sub.add_parser(
        "task", help="Upsert a task row in PROGRESS tasks table and recompute overview."
    )
    p_task.add_argument("--task-id", required=True)
    p_task.add_argument("--desc", required=True)
    p_task.add_argument("--risk", required=True, choices=["low", "medium", "high"])
    p_task.add_argument(
        "--status", required=True, choices=["IN_PROGRESS", "PASS", "FAIL", "BLOCKED"]
    )
    p_task.add_argument("--evidence", default="")

    sub.add_parser("render", help="Recompute overview progress/time from tasks table.")

    args = parser.parse_args()

    root = repo_root_from_script()
    progress_path = os.path.join(root, "PROGRESS.md")
    summary_path = os.path.join(root, "SUMMARY.md")

    progress_md = read_text(progress_path)
    summary_md = read_text(summary_path)

    if args.cmd == "event":
        progress_md = append_timeline_event(
            progress_md, args.subagent, args.phase, args.what, args.result, args.next
        )
        progress_md = recompute_overview(progress_md)
        summary_md = append_summary_event(
            summary_md, args.subagent, args.phase, args.what, args.result, args.next
        )

    elif args.cmd == "task":
        progress_md = upsert_task(
            progress_md, args.task_id, args.desc, args.risk, args.status, args.evidence
        )
        progress_md = recompute_overview(progress_md)
        # Also log a summary event for visibility
        summary_md = append_summary_event(
            summary_md,
            "system",
            "task",
            f"更新任务状态：{args.task_id} → {args.status}",
            (args.evidence[:120] + "…") if len(args.evidence) > 120 else args.evidence,
            "",
        )

    elif args.cmd == "render":
        progress_md = recompute_overview(progress_md)

    write_text(progress_path, progress_md)
    write_text(summary_path, summary_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
