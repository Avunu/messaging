# Copyright (c) 2023, Avunu LLC and Contributors
# See license.txt

"""Group Text Message: who receives it, when it goes out, and what it records (send_sms mocked)."""

from datetime import timedelta
from typing import Any, cast
from unittest.mock import patch

import frappe
from frappe import share
from frappe.tests.classes import IntegrationTestCase
from frappe.utils import now_datetime

from messaging.messaging.doctype.group_text_message import send_scheduled_messages
from messaging.messaging.doctype.group_text_message.group_text_message import GroupTextMessage
from messaging.tests.utils import as_user, make_contact, make_user, unique_phone

SEND_SMS = "messaging.messaging.doctype.group_text_message.group_text_message.send_sms"


def sent_to(numbers: list[str]) -> dict[str, Any]:
	return {"success": numbers, "errors": []}


class TestGroupTextMessage(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.group = self.make_group()
		self.reachable = self.member(self.group)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.flags.in_web_form = False
		frappe.db.rollback()

	def make_group(self) -> Any:
		return frappe.get_doc(
			{"doctype": "Messaging Group", "title": f"Texts {frappe.generate_hash(length=6)}"}
		).insert(ignore_permissions=True)

	def member(self, group: Any, consent: int = 1, valid: int = 1, mobile: bool = True) -> str:
		"""Add a contact to `group`; return its number."""
		phone = unique_phone()
		contact = make_contact(phone=phone, mobile=mobile, consent_sms=consent)
		frappe.db.set_value("Contact Phone", {"parent": contact.name}, "is_valid", valid)
		group.add_contact(contact.name)
		return phone

	def message(self, **fields: Any) -> GroupTextMessage:
		doc = frappe.get_doc(
			{
				"doctype": "Group Text Message",
				"message_title": "Closing early",
				"message": "We close at 3 today.",
				"messaging_group": [{"messaging_group": self.group.name}],
				**fields,
			}
		)
		return cast(GroupTextMessage, doc.insert())

	def test_submitting_sends_to_consenting_valid_mobiles_only(self) -> None:
		self.member(self.group, consent=0)
		self.member(self.group, valid=0)
		self.member(self.group, mobile=False)
		# a member of an excluded group is left out, even though it is in the message's group
		excluded_group = self.make_group()
		excluded = self.member(self.group)
		excluded_group.add_contact(frappe.db.get_value("Contact Phone", {"phone": excluded}, "parent"))

		doc = self.message(exclude_groups=[{"messaging_group": excluded_group.name}])
		with patch(SEND_SMS, return_value=sent_to([self.reachable])) as send:
			doc.submit()

		self.assertEqual(send.call_args.args[0], [self.reachable])
		doc.reload()
		self.assertEqual(doc.status, "Sent")
		self.assertTrue(doc.delivery_datetime)
		comment = frappe.get_last_doc("Comment", filters={"reference_name": doc.name})
		self.assertIn("Sent to 1 of 1", comment.content)

	def test_failed_numbers_are_recorded(self) -> None:
		result = {"success": [], "errors": [{"number": self.reachable, "code": 30003}]}
		doc = self.message()
		with patch(SEND_SMS, return_value=result):
			doc.submit()
		self.assertEqual(frappe.db.get_value("Group Text Message", doc.name, "status"), "Error")
		comment = frappe.get_last_doc("Comment", filters={"reference_name": doc.name})
		self.assertIn("error 30003", comment.content)

	def test_no_recipients_is_an_error(self) -> None:
		self.group = self.make_group()
		doc = self.message()
		with patch(SEND_SMS) as send:
			doc.submit()
		send.assert_not_called()
		self.assertEqual(frappe.db.get_value("Group Text Message", doc.name, "status"), "Error")

	def test_a_sending_failure_is_logged_as_an_error(self) -> None:
		doc = self.message()
		with patch(SEND_SMS, side_effect=RuntimeError("Twilio down")), patch("frappe.log_error") as log_error:
			doc.submit()
		log_error.assert_called_once()
		self.assertEqual(frappe.db.get_value("Group Text Message", doc.name, "status"), "Error")

	def test_a_scheduled_message_waits_for_the_scheduler(self) -> None:
		doc = self.message(schedule=1, delivery_datetime=now_datetime() + timedelta(hours=1))
		with patch(SEND_SMS) as send:
			doc.submit()
		send.assert_not_called()
		self.assertEqual(frappe.db.get_value("Group Text Message", doc.name, "status"), "Scheduled")

		with patch(SEND_SMS) as send:
			send_scheduled_messages()
		send.assert_not_called()

		frappe.db.set_value(
			"Group Text Message", doc.name, "delivery_datetime", now_datetime() - timedelta(minutes=1)
		)
		with patch(SEND_SMS, return_value=sent_to([self.reachable])) as send:
			send_scheduled_messages()
		send.assert_called_once()
		self.assertEqual(frappe.db.get_value("Group Text Message", doc.name, "status"), "Sent")

	def test_a_cancelled_scheduled_message_goes_back_to_draft(self) -> None:
		doc = self.message(schedule=1, delivery_datetime=now_datetime() + timedelta(hours=1))
		doc.submit()
		doc.reload()
		doc.cancel()
		self.assertEqual(frappe.db.get_value("Group Text Message", doc.name, "status"), "Draft")

	def test_a_schedule_in_the_past_is_refused(self) -> None:
		with self.assertRaises(frappe.ValidationError):
			self.message(schedule=1, delivery_datetime=now_datetime() - timedelta(hours=1))

	def test_a_web_form_submission_is_submitted_on_insert(self) -> None:
		frappe.flags.in_web_form = True
		with patch(SEND_SMS, return_value=sent_to([self.reachable])):
			doc = self.message()
		self.assertEqual(doc.docstatus, 1)

	def test_sending_directly_needs_submit_permission(self) -> None:
		doc = self.message()
		with patch(SEND_SMS, return_value=sent_to([self.reachable])):
			doc.submit()
		reader = make_user(roles=("Accounts User",))
		share.add("Group Text Message", doc.name, reader, read=1)
		with as_user(reader), self.assertRaises(frappe.PermissionError):
			cast(GroupTextMessage, frappe.get_doc("Group Text Message", str(doc.name))).send_text_message()
