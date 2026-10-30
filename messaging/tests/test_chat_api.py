# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The chat endpoints: what each returns, what each changes, and who may call it."""

import json
from typing import Any, cast
from unittest.mock import MagicMock, patch

import frappe
from frappe.core.doctype.communication.communication import Communication
from frappe.core.doctype.file.file import File
from frappe.realtime import get_doctype_room
from frappe.tests.classes import IntegrationTestCase

from messaging.messaging.api.chat import api
from messaging.tests.utils import (
	as_user,
	make_communication,
	make_contact,
	make_user,
	unique_phone,
)

TWILIO_SEND = "messaging.messaging.api.twilio_sms.send_sms"


class ChatTestCase(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.phone = unique_phone()
		self.room = f"SMS:{self.phone}"

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback()


class TestReads(ChatTestCase):
	def test_get_current_user_describes_the_session_user(self) -> None:
		user = api.get_current_user()
		self.assertEqual(user["_id"], "Administrator")
		self.assertIn("state", user["status"])
		self.assertTrue(user["avatar"])

	def test_get_rooms_groups_a_conversation_into_one_room(self) -> None:
		contact = make_contact(phone=self.phone)
		make_communication(phone_no=self.phone, content="first")
		make_communication(phone_no=self.phone, content="second")

		rooms = api.get_rooms(search=self.phone)["rooms"]

		room = next(r for r in rooms if r["roomId"] == self.room)
		self.assertEqual(room["unreadCount"], 2)
		self.assertEqual(room["contactName"], contact.name)
		self.assertTrue(room["hasUnreplied"])
		self.assertEqual(room["lastMessage"]["content"], "second")

	def test_get_rooms_filters_by_medium_and_pages(self) -> None:
		make_communication(phone_no=self.phone)
		email = f"{frappe.generate_hash(length=8)}@example.com"
		make_communication(medium="Email", sender=email, subject="Quote request")

		sms = api.get_rooms(medium="SMS", search=self.phone)
		self.assertTrue(all(r["communicationMedium"] == "SMS" for r in sms["rooms"]))
		mail = api.get_rooms(medium="Email", search=email)
		self.assertEqual([r["roomId"] for r in mail["rooms"]], [f"Email:{email}"])
		self.assertEqual(mail["rooms"][0]["lastMessage"]["content"], "Quote request")

		first = api.get_rooms(page=1, limit=1)
		self.assertEqual(len(first["rooms"]), 1)
		self.assertTrue(first["hasMore"])

	def test_get_rooms_finds_a_room_by_its_contacts_name(self) -> None:
		email = f"{frappe.generate_hash(length=8)}@example.com"
		contact = make_contact(email=email, first_name="Zebedee", last_name=frappe.generate_hash(length=6))
		make_communication(medium="Email", sender=email)

		rooms = api.get_rooms(search=f"Zebedee {contact.last_name}")["rooms"]

		self.assertIn(f"Email:{email}", [r["roomId"] for r in rooms])

	def test_search_rooms_returns_the_matching_rooms(self) -> None:
		make_communication(phone_no=self.phone)
		self.assertIn(self.room, [r["roomId"] for r in api.search_rooms(query=self.phone)])

	def test_get_messages_lists_the_room_oldest_first(self) -> None:
		first = make_communication(phone_no=self.phone, content="one")
		reply = make_communication(
			sent_or_received="Sent", phone_no=self.phone, content="two", in_reply_to=first.name
		)
		frappe.db.set_value("Communication", reply.name, "delivery_status", "Sent")

		result = api.get_messages(room_id=self.room)

		self.assertEqual([m["content"] for m in result["messages"]], ["one", "two"])
		self.assertEqual(result["total"], 2)
		sent = result["messages"][1]
		self.assertEqual(sent["sentOrReceived"], "Sent")
		self.assertTrue(sent["distributed"])

	def test_get_messages_pages_from_the_newest(self) -> None:
		for n in range(3):
			make_communication(phone_no=self.phone, content=f"m{n}")
		page = api.get_messages(room_id=self.room, page=1, limit=2)
		self.assertEqual([m["content"] for m in page["messages"]], ["m1", "m2"])
		self.assertTrue(page["hasMore"])
		older = api.get_messages(room_id=self.room, page=2, limit=2)
		self.assertEqual([m["content"] for m in older["messages"]], ["m0"])

	def test_get_messages_shows_an_emails_subject_attachment_and_reply(self) -> None:
		email = f"{frappe.generate_hash(length=8)}@example.com"
		first = make_communication(medium="Email", sender=email, subject="Invoice", content="<p>Hi</p>")
		second = make_communication(
			medium="Email",
			sender=email,
			subject="Re: Invoice",
			content="Thanks\n\nOn Mon, Jan 5, 2026 at 9:00 AM Someone wrote:\n> Hi",
			in_reply_to=first.name,
		)
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "quote.txt",
				"attached_to_doctype": "Communication",
				"attached_to_name": second.name,
				"content": b"the quote",
				"is_private": 1,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Communication", second.name, "has_attachment", 1)

		messages = api.get_messages(room_id=f"Email:{email}")["messages"]

		latest = messages[-1]
		self.assertTrue(latest["content"].startswith("**Re: Invoice**"))
		self.assertNotIn("wrote:", latest["content"])
		self.assertEqual(latest["files"][0]["extension"], "txt")
		self.assertEqual(latest["replyMessage"]["_id"], first.name)
		self.assertEqual(latest["replyMessage"]["content"], "Hi")

	def test_get_messages_of_an_invalid_room_is_empty(self) -> None:
		self.assertEqual(api.get_messages(room_id="")["messages"], [])

	def test_get_unread_count_counts_unseen_received_messages(self) -> None:
		before = api.get_unread_count()
		make_communication(phone_no=self.phone)
		make_communication(sent_or_received="Sent", phone_no=self.phone)
		self.assertEqual(api.get_unread_count(), before + 1)


class TestChanges(ChatTestCase):
	def test_send_message_by_sms_records_and_sends_it(self) -> None:
		received = make_communication(phone_no=self.phone, subject="Question")
		with patch(TWILIO_SEND, return_value={"success": [self.phone], "errors": []}) as send:
			result = api.send_message(room_id=self.room, content="On our way")

		self.assertTrue(result["success"], result["error"])
		message = result["message"]
		assert message is not None
		send.assert_called_once_with([self.phone], "On our way", success_msg=False)
		comm = cast(Communication, frappe.get_doc("Communication", message["_id"]))
		self.assertEqual((comm.communication_medium, comm.sent_or_received), ("SMS", "Sent"))
		self.assertEqual(comm.delivery_status, "Sent")
		self.assertEqual(comm.in_reply_to, received.name)
		self.assertEqual(frappe.db.get_value("Communication", received.name, "status"), "Replied")

	def test_send_message_records_an_sms_twilio_refused(self) -> None:
		failed = {"success": [], "errors": [{"status": "error", "number": self.phone, "code": 21610}]}
		with patch(TWILIO_SEND, return_value=failed):
			result = api.send_message(room_id=self.room, content="Hello")
		message = result["message"]
		assert message is not None
		self.assertEqual(frappe.db.get_value("Communication", message["_id"], "delivery_status"), "Error")

	def test_send_message_records_an_sms_that_raised(self) -> None:
		with patch(TWILIO_SEND, side_effect=RuntimeError("gateway down")):
			result = api.send_message(room_id=self.room, content="Hello")
		message = result["message"]
		assert message is not None
		self.assertEqual(frappe.db.get_value("Communication", message["_id"], "delivery_status"), "Error")

	def test_send_message_by_email_quotes_the_thread_and_signs_it(self) -> None:
		email = f"{frappe.generate_hash(length=8)}@example.com"
		make_communication(
			medium="Email",
			sender=email,
			subject="Booking",
			content="Can we move it?",
			recipients="us@example.com",
		)
		user = make_user(roles=("System Manager",))
		frappe.db.set_value("User", user, "email_signature", "<p>Jo Bloggs<br>Avunu</p>")

		with as_user(user), patch("frappe.sendmail") as sendmail:
			result = api.send_message(
				room_id=f"Email:{email}", content="Yes, Tuesday works.", files=json.dumps([])
			)

		self.assertTrue(result["success"], result["error"])
		message = result["message"]
		assert message is not None
		self.assertEqual(message["subject"], "Re: Booking")
		kwargs = sendmail.call_args.kwargs
		self.assertEqual(kwargs["recipients"], [email])
		comm = cast(Communication, frappe.get_doc("Communication", message["_id"]))
		self.assertIn("Jo Bloggs", comm.text_content or "")
		self.assertIn("> Can we move it?", comm.text_content or "")

	def test_send_message_attaches_the_files_it_was_given(self) -> None:
		# The chat uploads each file first (upload_file), then sends its name and URL.
		uploaded = cast(
			File,
			frappe.get_doc(
				{"doctype": "File", "file_name": "map.txt", "content": b"turn left", "is_private": 1}
			).insert(ignore_permissions=True),
		)
		with patch(TWILIO_SEND, return_value={"success": [self.phone], "errors": []}):
			result = api.send_message(
				room_id=self.room,
				content="See attached",
				files=[{"name": "map.txt", "url": uploaded.file_url}],
				subject="Directions",
			)
		message = result["message"]
		assert message is not None
		self.assertEqual(message["subject"], "Directions")
		self.assertTrue(
			frappe.db.exists("File", {"attached_to_name": message["_id"], "file_url": uploaded.file_url})
		)

	def test_send_message_to_an_invalid_room_fails(self) -> None:
		result = api.send_message(room_id="SMS", content="Hello")
		self.assertFalse(result["success"])

	def test_mark_messages_seen_marks_the_rooms_unseen_messages(self) -> None:
		a = make_communication(phone_no=self.phone)
		b = make_communication(phone_no=self.phone)
		self.assertEqual(api.mark_messages_seen(room_id=self.room), {"success": True, "count": 2})
		for comm in (a, b):
			self.assertEqual(frappe.db.get_value("Communication", comm.name, "seen"), 1)
		self.assertEqual(api.mark_messages_seen(room_id=self.room)["count"], 0)
		self.assertFalse(api.mark_messages_seen(room_id="")["success"])

	def test_archive_room_closes_every_message(self) -> None:
		comms = [make_communication(phone_no=self.phone) for _ in range(2)]
		self.assertEqual(api.archive_room(room_id=self.room)["count"], 2)
		for comm in comms:
			self.assertEqual(frappe.db.get_value("Communication", comm.name, "status"), "Closed")
		self.assertFalse(api.archive_room(room_id="")["success"])

	def test_delete_room_deletes_every_message(self) -> None:
		comms = [make_communication(phone_no=self.phone) for _ in range(2)]
		result = api.delete_room(room_id=self.room)
		self.assertEqual((result["success"], result["count"]), (True, 2))
		for comm in comms:
			self.assertFalse(frappe.db.exists("Communication", comm.name))
		self.assertFalse(api.delete_room(room_id="")["success"])


class TestNotifications(ChatTestCase):
	def test_a_new_communication_is_published_to_the_communication_room(self) -> None:
		with patch("frappe.publish_realtime") as publish:
			comm = make_communication(phone_no=self.phone)
		event = next(c for c in publish.call_args_list if c.args and c.args[0] == "new_communication")
		self.assertEqual(event.kwargs["room"], get_doctype_room("Communication"))
		self.assertEqual(event.args[1]["name"], comm.name)

	def test_a_comment_is_not_published(self) -> None:
		doc = frappe._dict(communication_type="Comment")
		with patch("frappe.publish_realtime") as publish:
			api.notify_new_communication(doc)
		publish.assert_not_called()

	def test_a_received_message_notifies_only_subscribers_who_can_read_it(self) -> None:
		reader = make_user(roles=("System Manager",))
		outsider = make_user()
		for user in (reader, outsider, "Guest"):
			frappe.get_doc(
				{
					"doctype": "Push Subscription",
					"user": user,
					"endpoint": f"https://push.example.com/{frappe.generate_hash(length=8)}",
					"subscription_json": "{}",
				}
			).insert(ignore_permissions=True)
		contact = make_contact(phone=self.phone)

		with patch("messaging.messaging.api.chat.push.send_push_to_user", return_value=1) as push:
			api._send_push_for_received(
				doc_name="COMM-1",
				sender=self.phone,
				phone_no=self.phone,
				content="<b>Running late</b>" + "!" * 300,
				medium="SMS",
			)

		users = [c.kwargs["user"] for c in push.call_args_list]
		self.assertIn(reader, users)
		self.assertNotIn(outsider, users)
		self.assertNotIn("Guest", users)
		call = next(c for c in push.call_args_list if c.kwargs["user"] == reader)
		self.assertEqual(call.kwargs["title"], contact.full_name)
		self.assertTrue(call.kwargs["body"].startswith("Running late"))
		self.assertTrue(call.kwargs["body"].endswith("..."))

	def test_a_failed_push_is_logged_and_the_rest_continue(self) -> None:
		reader = make_user(roles=("System Manager",))
		frappe.get_doc(
			{
				"doctype": "Push Subscription",
				"user": reader,
				"endpoint": f"https://push.example.com/{frappe.generate_hash(length=8)}",
				"subscription_json": "{}",
			}
		).insert(ignore_permissions=True)
		email = f"{frappe.generate_hash(length=8)}@example.com"
		with (
			patch("messaging.messaging.api.chat.push.send_push_to_user", side_effect=RuntimeError("boom")),
			patch("frappe.log_error") as log_error,
		):
			api._send_push_for_received(
				doc_name="COMM-2", sender=email, phone_no="", content="Hi", medium="Email", subject="Hello"
			)
		log_error.assert_called()


class TestPermissions(ChatTestCase):
	"""A user who may not read Communication reaches none of them through the chat."""

	def test_a_website_user_is_refused_every_endpoint(self) -> None:
		user = make_user()
		calls: list[tuple[Any, dict[str, Any]]] = [
			(api.get_current_user, {}),
			(api.get_rooms, {}),
			(api.get_messages, {"room_id": self.room}),
			(api.search_rooms, {"query": "x"}),
			(api.get_unread_count, {}),
			(api.send_message, {"room_id": self.room, "content": "x"}),
			(api.mark_messages_seen, {"room_id": self.room}),
			(api.archive_room, {"room_id": self.room}),
			(api.delete_room, {"room_id": self.room}),
		]
		with as_user(user):
			for fn, kwargs in calls:
				with self.subTest(fn.__name__), self.assertRaises(frappe.PermissionError):
					fn(**kwargs)

	def test_an_inbox_user_reads_but_cannot_archive(self) -> None:
		make_communication(phone_no=self.phone)
		user = make_user(roles=("Inbox User",))
		with as_user(user):
			self.assertIn(self.room, [r["roomId"] for r in api.get_rooms(search=self.phone)["rooms"]])
			with self.assertRaises(frappe.PermissionError):
				api.archive_room(room_id=self.room)


class TestRequestContract(IntegrationTestCase):
	"""The endpoints that change data accept POST only: frappe rolls back a GET's writes."""

	def test_mutating_endpoints_are_post_only(self) -> None:
		from messaging.messaging.api.chat import links, push
		from messaging.messaging.custom import contact
		from messaging.messaging.doctype.group_text_message.group_text_message import GroupTextMessage
		from messaging.messaging.doctype.messaging_settings.messaging_settings import MessagingSettings

		for fn in (
			api.send_message,
			api.mark_messages_seen,
			api.archive_room,
			api.delete_room,
			push.get_vapid_public_key,
			push.save_push_subscription,
			push.remove_push_subscription,
			contact.bulk_add_to_group,
			contact.bulk_remove_from_group,
			contact.Contact.add_to_group,
			contact.Contact.remove_from_group,
			GroupTextMessage.send_text_message,
			MessagingSettings.generate_vapid_keys,
		):
			with self.subTest(fn.__qualname__):
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
		for fn in (
			api.get_rooms,
			api.get_messages,
			push.get_push_subscription_status,
			links.get_linked_documents,
		):
			with self.subTest(fn.__qualname__):
				self.assertIn("GET", frappe.allowed_http_methods_for_whitelisted_func[fn])

	def test_a_get_to_a_mutating_endpoint_is_refused(self) -> None:
		from frappe.handler import is_valid_http_method

		request = MagicMock(method="GET")
		with patch.object(frappe.local, "request", request, create=True):
			with self.assertRaises(frappe.PermissionError):
				is_valid_http_method(api.delete_room)
			is_valid_http_method(api.get_rooms)
