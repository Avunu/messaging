# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The demo hook frappe-demo calls (`messaging.demo.setup`)."""

import datetime

import frappe
from frappe.tests.classes import IntegrationTestCase

from messaging import demo

CTX = {"today": datetime.date(2026, 1, 15), "seed": 1, "company": None, "erpnext_demo": False}


class TestDemo(IntegrationTestCase):
	def test_setup_builds_contacts_groups_conversations_and_group_texts(self):
		demo.setup(CTX)

		dana = frappe.db.get_value("Contact", {"first_name": "Dana", "last_name": "Whitfield"})
		self.assertEqual(frappe.db.get_value("Contact", dana, "mobile_no"), "+12025550134")
		phone = frappe.db.get_value(
			"Contact Phone", {"parent": dana}, ["is_valid", "carrier_type"], as_dict=True
		)
		assert phone is not None
		self.assertEqual((phone.is_valid, phone.carrier_type), (1, "mobile"))

		self.assertEqual(frappe.db.count("Messaging Group Member", {"parent": "Volunteers"}), 4)
		self.assertEqual(frappe.db.count("Messaging Group Member", {"parent": "Board Members"}), 2)

		thread = frappe.get_all(
			"Communication",
			filters={"communication_medium": "SMS", "phone_no": "+12025550134"},
			fields=["sent_or_received", "communication_date"],
			order_by="communication_date asc",
		)
		self.assertEqual([c.sent_or_received for c in thread], ["Received", "Sent", "Received", "Received"])
		self.assertEqual(thread[-1].communication_date, datetime.datetime(2026, 1, 15, 11, 15))
		self.assertEqual(
			frappe.db.count(
				"Communication",
				{
					"communication_type": "Communication",
					"sent_or_received": "Received",
					"seen": 0,
					"communication_date": ["between", ["2026-01-14", "2026-01-15 23:59:59"]],
				},
			),
			3,
		)

		sent = frappe.db.get_value(
			"Group Text Message",
			{"message_title": "Community dinner"},
			["name", "status", "docstatus"],
			as_dict=True,
		)
		assert sent is not None
		self.assertEqual((sent.status, sent.docstatus), ("Sent", 1))
		comment = frappe.db.get_value(
			"Comment", {"reference_doctype": "Group Text Message", "reference_name": sent.name}, "content"
		)
		# Priya gave no SMS consent, so three of the four volunteers receive it.
		self.assertIn("Sent to 3 of 3 recipients", str(comment))
		draft = frappe.db.get_value(
			"Group Text Message",
			{"message_title": "Food drive reminder"},
			["status", "docstatus"],
			as_dict=True,
		)
		assert draft is not None
		self.assertEqual((draft.status, draft.docstatus), ("Draft", 0))

	def test_setup_is_idempotent(self):
		demo.setup(CTX)
		before = frappe.db.count("Communication", {"communication_type": "Communication"})
		demo.setup(CTX)
		self.assertEqual(frappe.db.count("Communication", {"communication_type": "Communication"}), before)
		self.assertEqual(frappe.db.count("Contact", {"first_name": "Dana", "last_name": "Whitfield"}), 1)
		self.assertEqual(frappe.db.count("Group Text Message", {"message_title": "Community dinner"}), 1)
