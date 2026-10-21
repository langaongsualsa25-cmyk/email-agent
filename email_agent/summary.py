"""Builds a human-readable summary of a triage run."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .classifier import Category
from .gmail_client import EmailMessage


@dataclass
class TriageResult:
    message: EmailMessage
    category: Category
    drafted: bool


def build_summary(results: list[TriageResult]) -> str:
    if not results:
        return "No unread messages to triage. Inbox is clear."

    counts = Counter(r.category.name for r in results)
    drafted_count = sum(1 for r in results if r.drafted)

    lines = [
        f"Email Agent summary — {len(results)} unread message(s) processed",
        "-" * 60,
    ]
    for name, count in counts.most_common():
        lines.append(f"  {name:<16} {count}")
    lines.append("-" * 60)
    lines.append(f"Draft replies created: {drafted_count}")
    lines.append("")
    lines.append("Details:")

    for r in results:
        flag = " [drafted]" if r.drafted else ""
        lines.append(
            f"  [{r.category.name}]{flag} {r.message.subject!r} "
            f"from {r.message.sender}"
        )

    return "\n".join(lines)
