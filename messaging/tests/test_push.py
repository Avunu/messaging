# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Web push: the VAPID key pair, browser subscriptions, and delivery (pywebpush mocked)."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.classes import IntegrationTestCase
from pywebpush import WebPushException

from messaging.messaging.api.chat import push
from messaging.tests.utils import as_user, make_user, messaging_settings

WEBPUSH = "pywebpush.webpush"


def subscription(endpoint: str | None = None) -> dict[str, Any]:
	return {
		"endpoint": endpoint or f"https://push.example.com/{frappe.generate_hash(length=10)}",
		"keys": {"p256dh": "p256", "auth": "secret"},
	}


class TestPush(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_the_public_key_is_generated_once_and_kept(self) -> None:
		with messaging_settings(vapid_public_key=None, vapid_private_key_secret=None):
			key = push.get_vapid_public_key()
			self.assertTrue(key)
			self.assertNotIn("=", key)
			self.assertEqual(push.get_vapid_public_key(), key)
			settings = frappe.get_single("Messaging Settings")
			self.assertTrue(settings.get_password("vapid_private_key_secret"))

	def test_generate_vapid_keys_replaces_the_pair_and_needs_write(self) -> None:
		settings = frappe.get_single("Messaging Settings")
		before = settings.vapid_public_key
		with patch("frappe.msgprint"):
			settings.generate_vapid_keys()
		self.assertNotEqual(frappe.get_single("Messaging Settings").vapid_public_key, before)

		with as_user(make_user()), self.assertRaises(frappe.PermissionError):
			frappe.get_single("Messaging Settings").generate_vapid_keys()

	def test_a_subscription_is_saved_updated_and_removed(self) -> None:
		user = make_user(roles=("System Manager",))
		sub = subscription()
		with as_user(user):
			self.assertEqual(push.save_push_subscription(json.dumps(sub)), {"success": True})
			self.assertEqual(push.get_push_subscription_status(), {"subscribed": True, "count": 1})

			sub["keys"]["auth"] = "rotated"
			push.save_push_subscription(json.dumps(sub))
			self.assertEqual(push.get_push_subscription_status()["count"], 1)
			name = frappe.db.get_value("Push Subscription", {"user": user}, "name")
			self.assertEqual(frappe.db.get_value("Push Subscription", name, "auth_key"), "rotated")

			push.remove_push_subscription(sub["endpoint"])
			self.assertEqual(push.get_push_subscription_status(), {"subscribed": False, "count": 0})

	def test_a_subscription_needs_a_user_and_an_endpoint(self) -> None:
		with as_user("Guest"), self.assertRaises(frappe.PermissionError):
			push.save_push_subscription(json.dumps(subscription()))
		with self.assertRaises(frappe.ValidationError):
			push.save_push_subscription(json.dumps({"keys": {}}))


class TestSendPush(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.user = make_user(roles=("System Manager",))
		self.subs = []
		for _ in range(3):
			doc = frappe.get_doc(
				{
					"doctype": "Push Subscription",
					"user": self.user,
					"endpoint": subscription()["endpoint"],
					"subscription_json": json.dumps(subscription()),
				}
			).insert(ignore_permissions=True)
			self.subs.append(doc.name)

	def tearDown(self) -> None:
		frappe.db.rollback()

	def send(self) -> int:
		return push.send_push_to_user(self.user, "Title", "Body", room_id="SMS:+12025550100")

	def test_each_subscription_gets_the_payload(self) -> None:
		with messaging_settings(vapid_contact_email="ops@example.com"):
			push.get_vapid_public_key()
			with patch(WEBPUSH, return_value=MagicMock(status_code=201)) as webpush:
				self.assertEqual(self.send(), 3)
		payload = json.loads(webpush.call_args.kwargs["data"])
		self.assertEqual(payload["tag"], "messaging-chat-SMS:+12025550100")
		self.assertEqual(webpush.call_args.kwargs["vapid_claims"], {"sub": "mailto:ops@example.com"})

	def test_expired_subscriptions_are_deleted_and_failures_logged(self) -> None:
		push.get_vapid_public_key()
		results = [
			MagicMock(status_code=410),
			WebPushException("Push failed: 404 Not Found"),
			WebPushException("Push failed: 500 Server Error"),
		]
		with patch(WEBPUSH, side_effect=results), patch("frappe.log_error") as log_error:
			self.assertEqual(self.send(), 0)
		remaining = frappe.get_all("Push Subscription", filters={"user": self.user}, pluck="name")
		self.assertEqual(len(remaining), 1)
		log_error.assert_called_once()

	def test_an_unexpected_error_is_logged(self) -> None:
		push.get_vapid_public_key()
		with patch(WEBPUSH, side_effect=RuntimeError("socket")), patch("frappe.log_error") as log_error:
			self.assertEqual(self.send(), 0)
		self.assertEqual(log_error.call_count, 3)

	def test_nothing_is_sent_without_keys_or_subscriptions(self) -> None:
		with messaging_settings(vapid_public_key=None), patch("frappe.log_error") as log_error:
			self.assertEqual(self.send(), 0)
		log_error.assert_called_once()

		push.get_vapid_public_key()
		with messaging_settings(vapid_private_key_secret=None), patch("frappe.log_error"):
			frappe.db.delete(
				"__Auth", {"doctype": "Messaging Settings", "fieldname": "vapid_private_key_secret"}
			)
			self.assertEqual(self.send(), 0)

		push.get_vapid_public_key()
		self.assertEqual(push.send_push_to_user(make_user(), "T", "B"), 0)
