"""Command-line entry point: triage unread mail and print a summary."""

from __future__ import annotations

import argparse
import sys

import yaml

from .classifier import RuleSet, classify, needs_draft_reply
from .drafts import build_reply_draft
from .gmail_client import GmailClient, get_credentials
from .summary import TriageResult, build_summary


def load_rules(path: str) -> RuleSet:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return RuleSet.from_dict(raw)


def run(rules_path: str, credentials_path: str, token_path: str, dry_run: bool) -> int:
    rules = load_rules(rules_path)
    creds = get_credentials(credentials_path, token_path)
    client = GmailClient(creds)

    messages = client.list_unread(max_results=rules.max_messages_per_run)

    results = []
    for message in messages:
        category = classify(message, rules)
        drafted = False

        if not dry_run:
            client.apply_label(message.id, category.label)

        if needs_draft_reply(category, rules):
            if not dry_run:
                draft_body = build_reply_draft(message, category)
                client.create_draft_reply(message, draft_body)
            drafted = True

        results.append(TriageResult(message=message, category=category, drafted=drafted))

    print(build_summary(results))
    if dry_run:
        print("\n(dry run — no labels applied, no drafts created)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="email-agent",
        description="Triage unread Gmail: label, draft replies, summarize.",
    )
    parser.add_argument("--rules", default="rules.yaml", help="Path to rules.yaml")
    parser.add_argument("--credentials", default="credentials.json",
                         help="Path to OAuth client secret JSON")
    parser.add_argument("--token", default="token.json",
                         help="Path to cached OAuth token JSON")
    parser.add_argument("--dry-run", action="store_true",
                         help="Classify and summarize only; don't touch Gmail")
    args = parser.parse_args(argv)

    return run(args.rules, args.credentials, args.token, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
