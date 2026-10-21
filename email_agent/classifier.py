"""Rule-based email categorization, driven by rules.yaml."""

from __future__ import annotations

from dataclasses import dataclass

from .gmail_client import EmailMessage


@dataclass
class Category:
    name: str
    label: str
    keywords: list[str]
    senders: list[str]


@dataclass
class RuleSet:
    categories: list[Category]
    default_category_name: str
    default_category_label: str
    draft_reply_categories: set[str]
    max_messages_per_run: int

    @classmethod
    def from_dict(cls, raw: dict) -> "RuleSet":
        categories = [
            Category(
                name=c["name"],
                label=c["label"],
                keywords=[k.lower() for k in c.get("keywords", [])],
                senders=[s.lower() for s in c.get("senders", [])],
            )
            for c in raw.get("categories", [])
        ]
        default = raw.get("default_category", {"name": "uncategorized", "label": "Agent/Uncategorized"})
        return cls(
            categories=categories,
            default_category_name=default["name"],
            default_category_label=default["label"],
            draft_reply_categories=set(raw.get("draft_reply_categories", [])),
            max_messages_per_run=raw.get("max_messages_per_run", 50),
        )


def classify(message: EmailMessage, rules: RuleSet) -> Category:
    """Return the first matching category for `message`, or the default."""
    haystack = f"{message.subject} {message.snippet} {message.sender}".lower()

    for category in rules.categories:
        if any(keyword in haystack for keyword in category.keywords):
            return category
        if any(sender in message.sender.lower() for sender in category.senders):
            return category

    return Category(
        name=rules.default_category_name,
        label=rules.default_category_label,
        keywords=[],
        senders=[],
    )


def needs_draft_reply(category: Category, rules: RuleSet) -> bool:
    return category.name in rules.draft_reply_categories
