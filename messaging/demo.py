# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Demo data for frappe-demo and the screenshots in docs/screenshots/.

Nothing leaves the site: Twilio stays unconfigured, and the one group text is sent through a stand-in
for the app's `send_sms`. The demo adds:

- five contacts with a mobile number and an e-mail address. Their numbers are marked valid mobiles,
  as Twilio Lookup would mark them, and four of them consented to SMS;
- two Messaging Groups, "Volunteers" and "Board Members";
- the conversations the chat view shows: SMS and e-mail threads from the day before and the morning
  of the demo day, two of them with unread messages, and one from a number with no contact;
- a sent Group Text Message to the Volunteers, and a draft one to everyone but the board.
"""

import datetime
from typing import Any
from unittest.mock import patch

import frappe

# first name, last name, mobile, e-mail, consented to SMS
CONTACTS = (
	("Dana", "Whitfield", "+12025550134", "dana.whitfield@example.com", 1),
	("Ravi", "Menon", "+12025550178", "ravi.menon@example.com", 1),
	("Lena", "Ortiz", "+12025550112", "lena.ortiz@example.com", 1),
	("Marcus", "Lee", "+12025550165", "marcus.lee@example.com", 1),
	("Priya", "Shah", "+12025550191", "priya.shah@example.com", 0),
)
UNKNOWN_NUMBER = "+12025550147"
OFFICE = "office@example.com"

# title, members by first name
GROUPS = (
	("Volunteers", ("Dana", "Lena", "Marcus", "Priya")),
	("Board Members", ("Ravi", "Lena")),
)

# The conversations, oldest first: (days before the demo day, time, medium, first name or a number,
# direction, subject, text, seen)
MESSAGES: tuple[tuple[int, str, str, str, str, str, str, int], ...] = (
	(
		1,
		"14:05",
		"Email",
		"Lena",
		"Sent",
		"Board meeting agenda",
		"Hi Lena, the agenda for Thursday's board meeting is attached to the event. "
		"Could you add the budget review as the second item?",
		1,
	),
	(
		1,
		"16:42",
		"Email",
		"Lena",
		"Received",
		"Re: Board meeting agenda",
		"Done, the budget review is second now. I'll bring printed copies for everyone.",
		1,
	),
	(
		1,
		"18:20",
		"SMS",
		"Marcus",
		"Received",
		"",
		"Running 10 minutes late to set up tonight, sorry!",
		1,
	),
	(1, "18:23", "SMS", "Marcus", "Sent", "", "No problem, the doors open at 7.", 1),
	(
		0,
		"08:12",
		"SMS",
		"Dana",
		"Received",
		"",
		"Hi! Is the community dinner still on for Saturday?",
		1,
	),
	(
		0,
		"08:31",
		"SMS",
		"Dana",
		"Sent",
		"",
		"Yes, Saturday at 6 in the fellowship hall. Can you bring a side dish?",
		1,
	),
	(0, "08:47", "SMS", "Dana", "Received", "", "Happy to. I'll bring two!", 1),
	(
		0,
		"09:58",
		"Email",
		"Ravi",
		"Received",
		"Question about the annual report",
		"Hello, could you send me last year's annual report before the board meeting? "
		"I'd like to compare the attendance numbers.",
		0,
	),
	(
		0,
		"10:26",
		"SMS",
		UNKNOWN_NUMBER,
		"Received",
		"",
		"Hi, a friend gave me this number. How do I sign up for the volunteer texts?",
		0,
	),
	(
		0,
		"11:15",
		"SMS",
		"Dana",
		"Received",
		"",
		"Also, should I bring folding chairs?",
		0,
	),
)

SENT_TEXT = (
	"Volunteers: the community dinner is this Saturday at 6 in the fellowship hall. "
	"Please arrive by 5 to help set up. Reply STOP to opt out."
)
DRAFT_TEXT = "Reminder: the food drive starts Monday at 9. Drop-offs go to the side entrance."


def make_contact(first: str, last: str, mobile: str, email: str, consent: int) -> str:
	name = frappe.db.get_value("Contact", {"first_name": first, "last_name": last})
	if not name:
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": first,
				"last_name": last,
				"consent_sms": consent,
				"email_ids": [{"email_id": email, "is_primary": 1}],
				"phone_nos": [{"phone": mobile, "is_primary_mobile_no": 1, "is_primary_phone": 1}],
			}
		).insert(ignore_permissions=True)
		name = contact.name
	# What Twilio Lookup records for a valid mobile number when number validation is on.
	frappe.db.set_value(
		"Contact Phone",
		{"parent": name, "phone": mobile},
		{"is_valid": 1, "validated_number": mobile, "carrier_type": "mobile"},
	)
	return str(name)


def make_group(title: str, contacts: list[str]) -> None:
	if frappe.db.exists("Messaging Group", {"title": title}):
		return
	frappe.get_doc(
		{
			"doctype": "Messaging Group",
			"title": title,
			"members": [{"contact": contact} for contact in contacts],
		}
	).insert(ignore_permissions=True)


def mark_replied(medium: str, party: str) -> None:
	"""Mark the thread's latest received message Replied, as the chat does when a user answers it."""
	field = "phone_no" if medium == "SMS" else "sender"
	latest = frappe.get_all(
		"Communication",
		filters={"communication_medium": medium, field: party, "sent_or_received": "Received"},
		order_by="communication_date desc",
		limit=1,
		pluck="name",
	)
	if latest:
		frappe.db.set_value("Communication", latest[0], "status", "Replied")


def make_messages(today: datetime.date, contacts: dict[str, str]) -> None:
	for days_before, time, medium, party, direction, subject, text, seen in MESSAGES:
		when = datetime.datetime.combine(
			today - datetime.timedelta(days=days_before), datetime.time.fromisoformat(time)
		)
		if frappe.db.exists("Communication", {"communication_date": when, "communication_medium": medium}):
			continue
		contact = contacts.get(party)
		comm: dict[str, Any] = {
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": medium,
			"communication_date": when,
			"sent_or_received": direction,
			"content": text,
			"text_content": text,
			"seen": seen,
		}
		if contact:
			full_name, mobile, email = frappe.db.get_value(
				"Contact", contact, ["full_name", "mobile_no", "email_id"]
			)
		else:
			full_name, mobile, email = "", party, ""
		if medium == "SMS":
			# As the webhook and the chat write them: an incoming text is "SMS from <number>".
			comm["subject"] = f"SMS from {mobile}" if direction == "Received" else ""
			comm["phone_no"] = mobile
			if direction == "Received":
				comm.update(
					sender=full_name or mobile, sender_full_name=full_name, recipients="", status="Open"
				)
			else:
				comm.update(sender="Administrator", recipients=mobile, delivery_status="Sent")
		elif direction == "Received":
			comm.update(
				subject=subject, sender=email, sender_full_name=full_name, recipients=OFFICE, status="Open"
			)
		else:
			comm.update(subject=subject, sender="Administrator", recipients=email, status="Linked")
		if direction == "Sent":
			mark_replied(medium, mobile if medium == "SMS" else email)
		frappe.get_doc(comm).insert(ignore_permissions=True)


def make_group_texts() -> None:
	from messaging.messaging.doctype.group_text_message import group_text_message

	volunteers = frappe.db.get_value("Messaging Group", {"title": "Volunteers"})
	board = frappe.db.get_value("Messaging Group", {"title": "Board Members"})
	if not frappe.db.exists("Group Text Message", {"message_title": "Community dinner"}):

		def stand_in(numbers: list[str], message: str, success_msg: bool = True) -> dict[str, Any]:
			return {"success": list(numbers), "errors": []}

		with patch.object(group_text_message, "send_sms", stand_in):
			frappe.get_doc(
				{
					"doctype": "Group Text Message",
					"message_title": "Community dinner",
					"message": SENT_TEXT,
					"messaging_group": [{"messaging_group": volunteers}],
				}
			).insert(ignore_permissions=True).submit()
	if not frappe.db.exists("Group Text Message", {"message_title": "Food drive reminder"}):
		frappe.get_doc(
			{
				"doctype": "Group Text Message",
				"message_title": "Food drive reminder",
				"message": DRAFT_TEXT,
				"messaging_group": [{"messaging_group": volunteers}],
				"exclude_groups": [{"messaging_group": board}],
			}
		).insert(ignore_permissions=True)


def setup(ctx: dict[str, Any]) -> None:
	"""Build the demo. ctx: today (a datetime.date), seed, company, erpnext_demo."""
	today: datetime.date = ctx["today"]
	contacts = {
		first: make_contact(first, last, mobile, email, consent)
		for first, last, mobile, email, consent in CONTACTS
	}
	for title, members in GROUPS:
		make_group(title, [contacts[first] for first in members])
	make_messages(today, contacts)
	make_group_texts()
