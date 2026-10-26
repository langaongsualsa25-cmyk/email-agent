"""Thin wrapper around the Gmail API: auth, fetching, labeling, drafting."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

DEFAULT_CREDENTIALS_PATH = "credentials.json"
DEFAULT_TOKEN_PATH = "token.json"


@dataclass
class EmailMessage:
    """Just the fields the triage logic needs, extracted from a Gmail message."""

    id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    label_ids: list[str]


def get_credentials(
    credentials_path: str = DEFAULT_CREDENTIALS_PATH,
    token_path: str = DEFAULT_TOKEN_PATH,
) -> Credentials:
    """Load cached OAuth credentials, refreshing or running the browser
    consent flow if needed.

    `credentials_path` is the OAuth client secret downloaded from Google
    Cloud Console (Desktop app type). `token_path` is where the user's
    granted token is cached between runs.
    """
    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Missing OAuth client secret at '{credentials_path}'. "
                    "Download it from Google Cloud Console (OAuth client, "
                    "Desktop app type) and place it there. See README.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # The token holds a long-lived refresh token, so keep it owner-only.
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.chmod(token_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


class GmailClient:
    """Gmail operations needed by the triage pipeline."""

    def __init__(self, credentials: Credentials):
        self.service = build("gmail", "v1", credentials=credentials)
        self._label_cache: dict[str, str] = {}

    def list_unread(self, max_results: int = 50) -> list[EmailMessage]:
        """Return up to `max_results` unread inbox messages, newest first."""
        resp = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results)
            .execute()
        )
        message_ids = [m["id"] for m in resp.get("messages", [])]

        messages = []
        for mid in message_ids:
            full = (
                self.service.users()
                .messages()
                .get(userId="me", id=mid, format="metadata",
                     metadataHeaders=["Subject", "From"])
                .execute()
            )
            headers = {
                h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])
            }
            messages.append(
                EmailMessage(
                    id=full["id"],
                    thread_id=full["threadId"],
                    subject=headers.get("Subject", "(no subject)"),
                    sender=headers.get("From", "(unknown sender)"),
                    snippet=full.get("snippet", ""),
                    label_ids=full.get("labelIds", []),
                )
            )
        return messages

    def ensure_label(self, label_name: str) -> str:
        """Return the Gmail label ID for `label_name`, creating it (and any
        parent labels implied by '/' nesting) if it doesn't exist yet."""
        if label_name in self._label_cache:
            return self._label_cache[label_name]

        existing = self.service.users().labels().list(userId="me").execute()
        for label in existing.get("labels", []):
            self._label_cache[label["name"]] = label["id"]

        if label_name in self._label_cache:
            return self._label_cache[label_name]

        created = (
            self.service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        self._label_cache[label_name] = created["id"]
        return created["id"]

    def apply_label(self, message_id: str, label_name: str) -> None:
        label_id = self.ensure_label(label_name)
        self.service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": [label_id]}
        ).execute()

    def create_draft_reply(self, message: EmailMessage, body_text: str) -> str:
        """Create a Gmail draft replying to `message` with `body_text`.
        Returns the new draft's ID. The draft is NOT sent automatically."""
        reply_subject = message.subject
        if not reply_subject.lower().startswith("re:"):
            reply_subject = f"Re: {reply_subject}"

        mime_message = MIMEText(body_text)
        mime_message["to"] = message.sender
        mime_message["subject"] = reply_subject
        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        draft = (
            self.service.users()
            .drafts()
            .create(
                userId="me",
                body={"message": {"raw": raw, "threadId": message.thread_id}},
            )
            .execute()
        )
        return draft["id"]
