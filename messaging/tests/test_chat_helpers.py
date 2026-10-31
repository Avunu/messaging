# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The chat's room ids, user details and email formatting."""

from datetime import timedelta

import frappe
from frappe.tests.classes import IntegrationTestCase
from frappe.utils import now_datetime

from messaging.messaging.api.chat import formatting, helpers
from messaging.messaging.api.chat.send import get_user_email_signature
from messaging.tests.utils import make_user


class TestRoomIds(IntegrationTestCase):
	def test_a_room_id_round_trips(self) -> None:
		room = helpers.format_room_id("Email", "a@example.com", "Project", "PROJ-1")
		self.assertEqual(room, "Email:a@example.com:Project:PROJ-1")
		self.assertEqual(
			helpers.parse_room_id(room),
			{
				"medium": "Email",
				"identifier": "a@example.com",
				"reference_doctype": "Project",
				"reference_name": "PROJ-1",
			},
		)
		self.assertEqual(helpers.format_room_id("SMS", "+12025550100"), "SMS:+12025550100")


class TestUsers(IntegrationTestCase):
	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_status_and_avatar(self) -> None:
		user = make_user(roles=("System Manager",))
		self.assertEqual(helpers.get_user_status(user)["state"], "offline")
		self.assertEqual(helpers.get_user_status(None), {"state": "offline", "lastChanged": ""})

		frappe.db.set_value("User", user, "last_active", now_datetime())
		self.assertEqual(helpers.get_user_status(user)["state"], "online")
		frappe.db.set_value("User", user, "last_active", now_datetime() - timedelta(hours=1))
		self.assertEqual(helpers.get_user_status(user)["state"], "offline")

		self.assertTrue(helpers.get_user_avatar(user).endswith("default-avatar.png"))
		frappe.db.set_value("User", user, "user_image", "https://cdn.example.com/me.png")
		self.assertEqual(helpers.get_user_avatar(user), "https://cdn.example.com/me.png")
		frappe.db.set_value("User", user, "user_image", "/files/me.png")
		self.assertTrue(helpers.get_user_avatar(user).endswith("/files/me.png"))

	def test_email_signature(self) -> None:
		user = make_user(roles=("System Manager",))
		full_name = frappe.db.get_value("User", user, "full_name")
		self.assertEqual(get_user_email_signature(user), f"--\n{full_name}")
		frappe.db.set_value("User", user, "email_signature", "Jo\nAvunu")
		self.assertEqual(get_user_email_signature(user), "Jo\nAvunu")
		self.assertEqual(get_user_email_signature(""), "")
		self.assertEqual(get_user_email_signature("nobody@example.com"), "")


class TestFormatting(IntegrationTestCase):
	def test_quoted_replies_are_stripped(self) -> None:
		cases = {
			"Thanks!\n\n---On Monday, Jo wrote:\nold": "Thanks!",
			"Sure.\n\nOn Tue, Jan 6, 2026 at 9:00 AM Jo <jo@example.com> wrote:\n> old": "Sure.",
			"Ok\n> quoted\n> more": "Ok",
			"Fine\n\nFrom: Jo\nSent: Monday\nTo: Us\nSubject: Re": "Fine",
			"Hi​\n\nLeave this conversation": "Hi",
			"Body\n--\nJo Bloggs": "Body",
		}
		for raw, clean in cases.items():
			with self.subTest(raw=raw):
				self.assertEqual(formatting.strip_quoted_replies(raw), clean)
		self.assertEqual(formatting.strip_quoted_replies(""), "")

	def test_html_and_plain_text(self) -> None:
		self.assertEqual(formatting.html_to_plain_text("<p>a</p><div>b<br/>c</div>\n\n\n\n"), "a\nb\nc")
		self.assertEqual(formatting.html_to_plain_text(""), "")
		self.assertEqual(formatting.plain_text_to_html("a\nb"), "a<br>\nb")
		self.assertEqual(formatting.plain_text_to_html(""), "")

	def test_sms_text_turns_the_reply_box_html_into_plain_text(self) -> None:
		self.assertEqual(
			formatting.sms_text("<p>On our way &amp; parking</p><p>See you <strong>soon</strong></p><p></p>"),
			"On our way & parking\nSee you soon",
		)
		# Plain text, a "<" in it included, is sent as it is.
		self.assertEqual(formatting.sms_text("1 < 2 and 3 > 2"), "1 < 2 and 3 > 2")
		self.assertEqual(formatting.sms_text(""), "")

	def test_a_quoted_reply_block(self) -> None:
		quoted = formatting.build_quoted_reply("Yes", "<p>Can we?</p><p>Thanks</p>", "Jo", "May 1")
		self.assertEqual(quoted, "Yes\n\nOn May 1, Jo wrote:\n> Can we?\n> Thanks")
