# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Web Push notification API endpoints.

Handles VAPID key generation, push subscription management,
and sending push notifications to subscribed browsers.
"""

import json
from typing import Any, cast

import frappe

from messaging.messaging.doctype.messaging_settings.messaging_settings import (
	MessagingSettings,
)
from messaging.messaging.doctype.push_subscription.push_subscription import (
	PushSubscription,
)


@frappe.whitelist()
def get_vapid_public_key() -> str:
	"""
	Return the VAPID public key so the browser can subscribe to push.

	The key pair is stored in Messaging Settings. If no keys exist yet,
	a new pair is generated automatically.

	Returns:
	    The VAPID public key (base64url-encoded).
	"""
	settings = cast(MessagingSettings, frappe.get_single("Messaging Settings"))

	if not settings.vapid_public_key:
		_generate_vapid_keys(settings)

	assert settings.vapid_public_key, "VAPID public key should be set after generation"

	return settings.vapid_public_key


@frappe.whitelist()
def save_push_subscription(subscription: str) -> dict:
	"""
	Save or update a push subscription for the current user.

	Args:
	    subscription: JSON-encoded PushSubscription from the browser.

	Returns:
	    Success status dict.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Authentication required")

	sub_data = json.loads(subscription) if isinstance(subscription, str) else subscription
	endpoint = sub_data.get("endpoint", "")

	if not endpoint:
		frappe.throw("Invalid subscription: missing endpoint")

	# Check if this endpoint already exists for this user
	existing = frappe.db.exists(
		"Push Subscription",
		{"user": user, "endpoint": endpoint},
	)

	if existing:
		# Update existing subscription (keys may have rotated)
		push_subscription = cast(PushSubscription, frappe.get_doc("Push Subscription", str(existing)))
		push_subscription.subscription_json = json.dumps(sub_data)
		push_subscription.p256dh_key = sub_data.get("keys", {}).get("p256dh", "")
		push_subscription.auth_key = sub_data.get("keys", {}).get("auth", "")
		push_subscription.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Push Subscription",
				"user": user,
				"endpoint": endpoint,
				"subscription_json": json.dumps(sub_data),
				"p256dh_key": sub_data.get("keys", {}).get("p256dh", ""),
				"auth_key": sub_data.get("keys", {}).get("auth", ""),
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
	return {"success": True}


@frappe.whitelist()
def remove_push_subscription(endpoint: str) -> dict:
	"""
	Remove a push subscription (e.g. user revoked permission).

	Args:
	    endpoint: The push subscription endpoint URL.

	Returns:
	    Success status dict.
	"""
	user = frappe.session.user
	subs = frappe.get_all(
		"Push Subscription",
		filters={"user": user, "endpoint": endpoint},
		pluck="name",
	)
	for name in subs:
		frappe.delete_doc("Push Subscription", name, ignore_permissions=True)

	frappe.db.commit()
	return {"success": True}


@frappe.whitelist()
def get_push_subscription_status() -> dict:
	"""
	Check whether the current user has any active push subscriptions.

	Returns:
	    Dict with 'subscribed' bool and count.
	"""
	user = frappe.session.user
	count = frappe.db.count("Push Subscription", {"user": user})
	return {"subscribed": count > 0, "count": count}


# ---------------------------------------------------------------------------
# Internal helpers (not whitelisted)
# ---------------------------------------------------------------------------


def _generate_vapid_keys(settings: Any = None) -> None:
	"""Generate a new VAPID key pair and save to Messaging Settings."""
	import base64

	from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
	from pywebpush import Vapid

	vapid = Vapid()
	vapid.generate_keys()

	# Public key: uncompressed EC point, base64url-encoded (no padding)
	assert vapid.public_key is not None
	pub_bytes = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
	public_key = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode("ascii")

	# Private key: raw 32-byte scalar, base64url-encoded (no padding)
	priv_numbers = vapid.private_key.private_numbers()
	priv_bytes = priv_numbers.private_value.to_bytes(32, "big")
	private_key = base64.urlsafe_b64encode(priv_bytes).rstrip(b"=").decode("ascii")

	if settings is None:
		settings = frappe.get_single("Messaging Settings")

	settings.vapid_public_key = public_key
	settings.vapid_private_key_secret = private_key
	settings.save(ignore_permissions=True)
	frappe.db.commit()


def send_push_to_user(
	user: str,
	title: str,
	body: str,
	room_id: str = "",
	communication_name: str = "",
	url: str = "/app/communication/view/chat",
	icon: str = "",
) -> int:
	"""
	Send a push notification to all subscriptions for a given user.

	Args:
	    user: The Frappe user (email) to notify.
	    title: Notification title.
	    body: Notification body text.
	    room_id: Chat room identifier for deep-linking.
	    communication_name: Communication doc name.
	    url: URL to open on click.
	    icon: Notification icon URL.

	Returns:
	    Number of successfully delivered push messages.
	"""
	settings = cast(MessagingSettings, frappe.get_single("Messaging Settings"))

	if not settings.vapid_public_key:
		frappe.log_error("VAPID keys not configured", "Push Notification Failed")
		return 0

	vapid_private_key = settings.get_password("vapid_private_key_secret")
	if not vapid_private_key:
		frappe.log_error("VAPID private key not set", "Push Notification Failed")
		return 0

	subscriptions = frappe.get_all(
		"Push Subscription",
		filters={"user": user},
		fields=["name", "endpoint", "subscription_json"],
	)

	if not subscriptions:
		return 0

	payload = json.dumps(
		{
			"title": title,
			"body": body,
			"room_id": room_id,
			"communication_name": communication_name,
			"url": url,
			"icon": icon,
			"tag": f"messaging-chat-{room_id}" if room_id else "messaging-chat-general",
		}
	)

	vapid_claims: dict[str, str | int] = {
		"sub": f"mailto:{settings.vapid_contact_email or frappe.session.user}",
	}

	sent = 0
	stale_subs: list[str] = []

	from pywebpush import WebPushException, webpush

	private_key_str = str(vapid_private_key)

	for sub in subscriptions:
		try:
			sub_info = json.loads(sub.subscription_json)
			resp = webpush(
				subscription_info=sub_info,
				data=payload,
				vapid_private_key=private_key_str,
				vapid_claims=vapid_claims,
			)
			if not isinstance(resp, str) and resp.status_code in (200, 201):
				sent += 1
			elif not isinstance(resp, str) and resp.status_code in (404, 410):
				# Subscription expired or unsubscribed
				stale_subs.append(sub.name)
		except WebPushException as e:
			if "410" in str(e) or "404" in str(e):
				stale_subs.append(sub.name)
			else:
				frappe.log_error(
					f"Push notification failed for {user}: {e}",
					"Push Notification Error",
				)
		except Exception as e:
			frappe.log_error(
				f"Push notification failed for {user}: {e}",
				"Push Notification Error",
			)

	# Clean up stale subscriptions
	for name in stale_subs:
		frappe.delete_doc("Push Subscription", name, ignore_permissions=True)

	if stale_subs:
		frappe.db.commit()

	return sent
