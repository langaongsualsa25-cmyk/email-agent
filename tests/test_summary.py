import unittest

from email_agent.classifier import Category
from email_agent.gmail_client import EmailMessage
from email_agent.summary import TriageResult, build_summary


def make_result(name, drafted, subject="Subject"):
    category = Category(name=name, label=f"Agent/{name}", keywords=[], senders=[])
    message = EmailMessage(
        id="1", thread_id="1", subject=subject, sender="a@example.com",
        snippet="", label_ids=[],
    )
    return TriageResult(message=message, category=category, drafted=drafted)


class SummaryTests(unittest.TestCase):
    def test_empty_inbox_message(self):
        self.assertIn("No unread messages", build_summary([]))

    def test_counts_and_drafted_total(self):
        results = [
            make_result("urgent", drafted=True),
            make_result("urgent", drafted=True),
            make_result("promo", drafted=False),
        ]
        text = build_summary(results)
        self.assertIn("3 unread message(s)", text)
        self.assertIn("urgent", text)
        self.assertIn("Draft replies created: 2", text)

    def test_details_list_each_message(self):
        results = [make_result("fyi", drafted=False, subject="Hello world")]
        text = build_summary(results)
        self.assertIn("Hello world", text)


if __name__ == "__main__":
    unittest.main()
