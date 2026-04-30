from __future__ import annotations

from datetime import datetime


def _today() -> str:
    return datetime.now().strftime("%d %B %Y")


def intern_prompt(metrics: dict) -> str:
    today = _today()
    return f"""
You are an AI mentor for interns.

DATE: {today}

Use ONLY the metrics provided. Do NOT invent numbers.

METRICS:
- Total Tasks: {metrics.get("tasks_total")}
- Completed: {metrics.get("tasks_completed")}
- In Progress: {metrics.get("tasks_inprogress")}
- Pending: {metrics.get("tasks_pending")}
- Completion Rate: {metrics.get("completion_rate")}%

Write a concise markdown summary with:
- Performance summary (2-4 sentences)
- Drawbacks (bullets)
- Suggestions (bullets)
- Improvement tips (bullets)
- Performance level based on completion rate: >70 good, 40-70 average, <40 needs improvement
- Final line: 1 motivational sentence
""".strip()


def employee_prompt(metrics: dict) -> str:
    today = _today()
    return f"""
You are an analytics assistant for an Employee Management System.

DATE: {today}

Use ONLY the metrics provided. Do NOT invent numbers.

METRICS:
- Total Tasks: {metrics.get("tasks_total")}
- Completed: {metrics.get("tasks_completed")}
- In Progress: {metrics.get("tasks_inprogress")}
- Pending: {metrics.get("tasks_pending")}
- Completion Rate: {metrics.get("completion_rate")}%

Write a professional markdown summary that includes:
- Short performance snapshot (2-4 sentences)
- Key observations (3-5 bullets)
- Next week action plan (3-7 bullets)
- Workload balance and likely blockers (bullets)
""".strip()


def teamlead_prompt(metrics: dict) -> str:
    today = _today()
    return f"""
You are an AI assistant helping a Team Lead improve team delivery.

DATE: {today}

Use ONLY the metrics provided. Do NOT invent numbers.

TEAM METRICS:
- Total Tasks: {metrics.get("tasks_total")}
- Completed: {metrics.get("tasks_completed")}
- In Progress: {metrics.get("tasks_inprogress")}
- Pending: {metrics.get("tasks_pending")}
- Completion Rate: {metrics.get("completion_rate")}%

Write a markdown summary with:
- Team-level snapshot (2-4 sentences)
- Bottlenecks and risks (bullets)
- Distribution analysis (pending vs inprogress vs completed) (bullets)
- Concrete leadership actions (3-7 bullets)
""".strip()


def md_prompt(metrics: dict) -> str:
    today = _today()
    return f"""
You are an AI Managing Director analyzing an organization dashboard.

DATE: {today}

Use ONLY the metrics provided. Do NOT invent numbers.

ORG METRICS:
{metrics}

Generate a structured markdown summary with clear sections and actionable improvements.
""".strip()


def prompt_for_type(summary_type: str, metrics: dict) -> str:
    st = (summary_type or "").strip().lower()
    if st == "intern":
        return intern_prompt(metrics)
    if st == "employee":
        return employee_prompt(metrics)
    if st == "teamlead":
        return teamlead_prompt(metrics)
    if st == "md":
        return md_prompt(metrics)
    raise ValueError("invalid summary type")

