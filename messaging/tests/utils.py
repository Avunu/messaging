# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Fixtures shared by the app's tests: users, contacts, communications and settings."""

import random
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

import frappe
from frappe.utils import random_string

from messaging.messaging.custom.contact import Contact


def unique_phone() -> str:
	"""A valid US number in E.164 that no other test uses."""
	return f"+1202555{random.randint(1000, 9999)}"


def make_user(roles: tuple[str, ...] = (), user_type: str | None = None) -> str:
	"""Create a user with `roles`; with none, a Website User. Returns the user's name."""
	email = f"msg-{random_string(8).lower()}@example.com"
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Test",
			"last_name": random_string(5),
			"send_welcome_email": 0,
			"user_type": user_type or ("System User" if roles else "Website User"),
			"roles": [{"role": role} for role in roles],
		}
	)
	user.insert(ignore_permissions=True)
	return str(user.name)


def make_contact(
	phone: str | None = None, email: str | None = None, mobile: bool = True, **fields: Any
) -> Contact:
	"""Insert a Contact with an optional phone and email."""
	doc: dict[str, Any] = {
		"doctype": "Contact",
		"first_name": f"Test{random_string(6)}",
		"last_name": "Contact",
		**fields,
	}
	contact = cast(Contact, frappe.get_doc(doc))
	if phone:
		contact.append("phone_nos", {"phone": phone, "is_primary_mobile_no": int(mobile)})
	if email:
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
	contact.insert(ignore_permissions=True)
	return contact


def make_communication(medium: str = "SMS", sent_or_received: str = "Received", **fields: Any) -> Any:
	"""Insert a Communication of type Communication, as the webhook or the chat writes one."""
	doc: dict[str, Any] = {
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": medium,
		"sent_or_received": sent_or_received,
		"subject": fields.pop("subject", f"{medium} {random_string(5)}"),
		"content": fields.pop("content", "Hello there"),
		**fields,
	}
	comm = frappe.get_doc(doc)
	comm.insert(ignore_permissions=True)
	return comm


@contextmanager
def messaging_settings(**values: Any) -> Generator[Any]:
	"""Set Messaging Settings fields for the block, and put the old values back afterwards."""
	settings = frappe.get_single("Messaging Settings")
	passwords = {
		k
		for k, v in values.items()
		if settings.meta.get_field(k) and settings.meta.get_field(k).fieldtype == "Password"
	}
	old = {k: settings.get(k) for k in values if k not in passwords}
	settings.update(values)
	settings.save(ignore_permissions=True)
	try:
		yield settings
	finally:
		settings = frappe.get_single("Messaging Settings")
		settings.update(old)
		for field in passwords:
			settings.set(field, None)
		settings.save(ignore_permissions=True)


@contextmanager
def as_user(user: str) -> Generator[None]:
	"""Run the block as `user`, then as Administrator again."""
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user("Administrator")
