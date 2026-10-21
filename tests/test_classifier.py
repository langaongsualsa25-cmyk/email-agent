import unittest

from email_agent.classifier import RuleSet, classify, needs_draft_reply
from email_agent.gmail_client import EmailMessage

RAW_RULES = {
    "categories": [
        {
            "name": "urgent",
            "label": "Agent/Urgent",
            "keywords": ["urgent", "asap"],
            "senders": [],
        },
        {
            "name": "needs_reply",
            "label": "Agent/Needs-Reply",
            "keywords": ["please respond", "?"],
            "senders": [],
        },
        {
            "name": "promo",
            "label": "Agent/Promo-Spam",
            "keywords": ["unsubscribe", "% off"],
            "senders": ["deals@shop.example"],
        },
    ],
    "default_category": {"name": "uncategorized", "label": "Agent/Uncategorized"},
    "draft_reply_categories": ["needs_reply", "urgent"],
    "max_messages_per_run": 50,
}


def make_message(subject="", snippet="", sender="someone@example.com") -> EmailMessage:
    return EmailMessage(
        id="1", thread_id="1", subject=subject, sender=sender,
        snippet=snippet, label_ids=[],
    )


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.rules = RuleSet.from_dict(RAW_RULES)

    def test_urgent_keyword_in_subject_wins(self):
        msg = make_message(subject="URGENT: server is down")
        category = classify(msg, self.rules)
        self.assertEqual(category.name, "urgent")

    def test_question_mark_flags_needs_reply(self):
        msg = make_message(subject="Are you free Thursday?")
        category = classify(msg, self.rules)
        self.assertEqual(category.name, "needs_reply")

    def test_sender_match_for_promo(self):
        msg = make_message(subject="Weekly picks", sender="deals@shop.example")
        category = classify(msg, self.rules)
        self.assertEqual(category.name, "promo")

    def test_falls_back_to_default(self):
        msg = make_message(subject="Project notes", snippet="attached as discussed")
        category = classify(msg, self.rules)
        self.assertEqual(category.name, "uncategorized")

    def test_first_matching_category_wins_over_later_ones(self):
        # Contains both an urgent keyword and a question mark; urgent is listed first.
        msg = make_message(subject="urgent - can you confirm?")
        category = classify(msg, self.rules)
        self.assertEqual(category.name, "urgent")

    def test_needs_draft_reply_for_configured_categories(self):
        msg = make_message(subject="urgent issue")
        category = classify(msg, self.rules)
        self.assertTrue(needs_draft_reply(category, self.rules))

    def test_no_draft_reply_for_promo(self):
        msg = make_message(subject="50% off", sender="deals@shop.example")
        category = classify(msg, self.rules)
        self.assertFalse(needs_draft_reply(category, self.rules))


if __name__ == "__main__":
    unittest.main()
