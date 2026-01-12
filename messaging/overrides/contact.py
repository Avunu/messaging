import json
from typing import TypedDict

import frappe
from frappe.contacts.doctype.contact.contact import Contact as BaseContact
from frappe.types import DF

from messaging.messaging.doctype.messaging_group.messaging_group import MessagingGroup


class MessageResponse(TypedDict):
	status: str
	message: str


class Contact(BaseContact):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		consent_sms: DF.Check

	# end: auto-generated types

	@frappe.whitelist()
	def add_to_group(self, group_name: str) -> None:
		"""Add contact to messaging group"""
		mg: MessagingGroup = MessagingGroup("Messaging Group", group_name)
		mg.add_contact(self.name)

	@frappe.whitelist()
	def remove_from_group(self, group_name: str) -> None:
		"""Remove contact from messaging group"""
		mg: MessagingGroup = MessagingGroup("Messaging Group", group_name)
		mg.remove_contact(self.name)


@frappe.whitelist()
def bulk_add_to_group(doc_names: str, group_name: str) -> MessageResponse:
	"""Add multiple contacts to a messaging group"""
	doc_names_list: list[str] = json.loads(doc_names)
	mg: MessagingGroup = MessagingGroup("Messaging Group", group_name)
	mg.add_contacts(doc_names_list)
	return {
		"status": "Success",
		"message": frappe._("Added contacts to group"),
	}


@frappe.whitelist()
def bulk_remove_from_group(doc_names: str, group_name: str) -> MessageResponse:
	"""Remove multiple contacts from a messaging group"""
	doc_names_list: list[str] = json.loads(doc_names)
	mg: MessagingGroup = MessagingGroup("Messaging Group", group_name)
	mg.remove_contacts(doc_names_list)
	return {
		"status": "Success",
		"message": frappe._("Removed contacts from group"),
	}


def add_to_all_contacts_group(doc: Contact, method: str | None = None) -> None:
	"""Add contact to all contacts group on creation"""
	all_contacts_group: str = str(frappe.db.get_single_value("Messaging Settings", "all_contacts_group"))
	if all_contacts_group:
		doc.add_to_group(all_contacts_group)
