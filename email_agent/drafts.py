"""Generates a short, generic reply-suggestion draft for messages that need one.

This is intentionally simple and template-based (no external LLM call), so
the project works offline/free out of the box. Swap `build_reply_draft`
for a call to your LLM provider of choice if you want sharper drafts.
"""

from __future__ import annotations

from .classifier import Category
from .gmail_client import EmailMessage


def build_reply_draft(message: EmailMessage, category: Category) -> str:
    """Return placeholder reply text for a human to review and edit before sending."""
    sender_name = message.sender.split("<")[0].strip().strip('"') or "there"

    if category.name == "urgent":
        opening = (
            f"Hi {sender_name},\n\n"
            "Thanks for flagging this — I'm looking into it now and will "
            "follow up with specifics shortly."
        )
    else:
        opening = (
            f"Hi {sender_name},\n\n"
            "Thanks for your message. "
        )

    body = (
        f"{opening}\n\n"
        f"[DRAFT — reference: \"{message.subject}\"]\n"
        "[Fill in your actual response here before sending.]\n\n"
        "Best,\n"
    )
    return body
