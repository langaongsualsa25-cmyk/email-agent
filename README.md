# email-agent

A small, rule-based Gmail triage assistant. It reads your unread inbox,
categorizes each message, applies a Gmail label for the category, drafts
a reply suggestion for messages that look like they need a response, and
prints a daily summary.

No external LLM calls, no server to run — it's a CLI you run locally or
on a schedule (cron, Task Scheduler, GitHub Actions, etc.).

## What it does

1. Fetches unread messages from your Gmail inbox (via the Gmail API).
2. Classifies each one against the rules in [`rules.yaml`](rules.yaml):
   `urgent`, `needs_reply`, `fyi`, `promo`, or `uncategorized` by default.
3. Applies a matching Gmail label (e.g. `Agent/Urgent`), creating it if needed.
4. For categories listed under `draft_reply_categories` in `rules.yaml`,
   creates a **draft** reply (never sends automatically) so you can review
   and send it yourself.
5. Prints a summary of what it found and did.

## Setup

1. **Create Google Cloud OAuth credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
   - Enable the **Gmail API** for your project.
   - Create an **OAuth client ID** of type **Desktop app**.
   - Download the JSON and save it as `credentials.json` in this project's
     root directory. (It's gitignored — never commit it.)

2. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run it**

   ```bash
   python -m email_agent.cli
   ```

   The first run opens a browser window for you to grant Gmail access.
   A `token.json` is cached afterward so you won't be prompted again
   until it expires.

   Try a dry run first (no labels applied, no drafts created):

   ```bash
   python -m email_agent.cli --dry-run
   ```

## Configuring the rules

Edit [`rules.yaml`](rules.yaml) — no code changes needed:

- `categories`: ordered list of `{name, label, keywords, senders}`. The
  first category whose keyword or sender pattern matches a message wins.
- `default_category`: applied when nothing matches.
- `draft_reply_categories`: which category names get an auto-drafted
  reply suggestion.
- `max_messages_per_run`: cap on how many unread messages are processed
  per run.

## Running on a schedule

This is a plain CLI, so you can wire it into cron, Windows Task
Scheduler, or a GitHub Actions scheduled workflow. Make sure
`credentials.json` and a pre-authorized `token.json` are available
wherever it runs (keep both out of version control).

## Running tests

```bash
python -m unittest discover -s tests
```

## Project layout

```
email_agent/
  gmail_client.py   # Gmail API auth, fetch, label, draft
  classifier.py      # rule-based categorization (rules.yaml-driven)
  drafts.py           # template-based reply draft text
  summary.py          # run summary report
  cli.py               # entry point
rules.yaml            # editable triage rules
tests/                  # unit tests for classifier + summary
```

## Notes & limitations

- Classification is keyword/sender rule-based, not ML/LLM-based — simple,
  predictable, and free to run, but it won't catch nuance a human (or an
  LLM) would. Tune `rules.yaml` as you see false positives/negatives.
- Drafts are template placeholders meant for a human to fill in and send
  — the tool never sends mail on its own.
- Requires the `gmail.modify` and `gmail.compose` OAuth scopes (labeling
  and drafting); it does not request `gmail.send` or delete access.
