# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The Newsletter extension's merge tags, and why rendering its message is safe."""

from typing import Any, cast
from unittest.mock import patch

import frappe
from frappe.tests.classes import IntegrationTestCase

from messaging.messaging.custom.newsletter import Newsletter
from messaging.tests.utils import make_contact


class TestNewsletterMergeTags(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.email = f"{frappe.generate_hash(length=8)}@example.com"
		self.contact = make_contact(
			email=self.email, first_name="Ada", last_name="Lovelace", company_name="Engines"
		)

	def tearDown(self) -> None:
		frappe.db.rollback()

	def newsletter(self, **fields: Any) -> Newsletter:
		return cast(
			Newsletter,
			frappe.get_doc(
				{
					"doctype": "Newsletter",
					"subject": "Spring news",
					"sender_email": "news@example.com",
					"content_type": "Rich Text",
					"message": "<p>Dear {{ first_name }} of {{ company_name }}, {{ doc.subject }}</p>",
					**fields,
				}
			),
		)

	def test_the_contact_map_holds_each_known_recipient(self) -> None:
		doc = self.newsletter()
		contacts = doc.get_contact_map([self.email, "stranger@example.com"])
		self.assertEqual(list(contacts), [self.email])
		self.assertEqual(contacts[self.email]["company_name"], "Engines")
		self.assertEqual(doc.get_contact_map([]), {})

	def test_the_message_merges_the_contacts_fields(self) -> None:
		doc = self.newsletter()
		html = doc.get_message(medium="email", contact=doc.get_contact_map([self.email])[self.email])
		self.assertIn("Dear Ada of Engines, Spring news", html)

		md = self.newsletter(content_type="Markdown", message_md="**Hi {{ first_name }}**")
		self.assertIn("<strong>Hi Ada</strong>", md.get_message(contact={"first_name": "Ada"}))
		raw = self.newsletter(content_type="HTML", message_html="<b>{{ full_name }}</b>")
		self.assertIn(
			"<b>stranger</b>", raw.get_message(contact=raw._get_default_contact("stranger@example.com"))
		)

	def test_recipient_data_is_a_value_never_a_template(self) -> None:
		# A contact can be created from an inbound email or a web form, so its fields are not
		# trusted; they reach the template as context values, which Jinja does not evaluate.
		doc = self.newsletter()
		html = doc.get_message(contact={"first_name": "{{ 7 * 7 }}", "company_name": "{% raw %}x"})
		self.assertIn("Dear {{ 7 * 7 }} of {% raw %}x", html)
		self.assertNotIn("49", html)

	def test_the_message_renders_in_frappes_sandbox(self) -> None:
		# The template itself is the Newsletter's message, written by a user who may write
		# Newsletters; frappe still refuses Python attribute access in it.
		doc = self.newsletter(message="{{ ''.__class__.__mro__ }}")
		with self.assertRaises(frappe.ValidationError):
			doc.get_message(contact={})

	def test_send_newsletter_queues_one_merged_email_per_recipient(self) -> None:
		audience = frappe.get_doc(
			{"doctype": "Email Group", "title": f"News {frappe.generate_hash(length=6)}"}
		).insert(ignore_permissions=True)
		doc = self.newsletter(email_group=[{"email_group": audience.name}])
		doc.insert(ignore_permissions=True)
		with patch("frappe.sendmail") as sendmail:
			# frappe passes a comma-separated string when a newsletter is sent from the form
			doc.send_newsletter(cast(Any, f"{self.email}, {self.email}, other@example.com"))
		self.assertEqual(sendmail.call_count, 2)
		by_recipient = {c.kwargs["recipients"][0]: c.kwargs for c in sendmail.call_args_list}
		self.assertIn("Dear Ada of Engines", by_recipient[self.email]["args"]["message"])
		self.assertIn("Dear  of ", by_recipient["other@example.com"]["args"]["message"])
		self.assertTrue(by_recipient[self.email]["email_read_tracker_url"])

		with patch("frappe.sendmail") as sendmail:
			doc.send_newsletter([self.email], test_email=True)
		self.assertIsNone(sendmail.call_args.kwargs["email_read_tracker_url"])
