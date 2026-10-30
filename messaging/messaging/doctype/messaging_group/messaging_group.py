# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import Contact
from frappe.email.doctype.email_group_member.email_group_member import EmailGroupMember
from frappe.model.document import Document
from frappe.query_builder import DocType


class MessagingGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from messaging.messaging.doctype.messaging_group_member.messaging_group_member import (
			MessagingGroupMember,
		)

		email_group: DF.Link | None
		members: DF.TableMultiSelect[MessagingGroupMember]
		title: DF.Data | None
	# end: auto-generated types

	# on validate, prune orphaned members and unlink any removed contacts
	def validate(self):
		# drop member rows whose Contact no longer exists before Frappe's
		# _validate_links() runs on save
		self.prune_orphaned_members()
		# get the messaging group members from before the update
		previous_members = frappe.get_all(
			"Messaging Group Member",
			filters={"parent": self.name},
			pluck="contact",
		)
		if not previous_members:
			return
		# check for members that were removed
		for previous_member in previous_members:
			if previous_member not in [
				messaging_group_member.contact for messaging_group_member in self.members
			]:
				self.unlink_contact_from_messaging_group(previous_member)

	def prune_orphaned_members(self):
		"""Remove member rows that reference a Contact which no longer exists.

		Frappe's _validate_links() re-validates every row in the members table on
		save, so a single dangling reference (e.g. a Contact removed via raw SQL or
		a force delete that skips Contact.on_trash) would otherwise block ALL saves
		of this group -- including adding new members -- with a LinkValidationError.
		"""
		valid_members = [
			member
			for member in self.members
			if member.contact and frappe.db.exists("Contact", member.contact)
		]
		if len(valid_members) != len(self.members):
			for member in self.members:
				if member not in valid_members:
					frappe.logger("messaging").warning(
						f"Messaging Group {self.name!r}: pruning orphaned member "
						f"referencing missing Contact {member.contact!r}"
					)
			self.members = valid_members

	def on_update(self):
		# if there are no members left, end function
		if not self.members:
			return

		# link the messaging group to the associated contacts
		for messaging_group_member in self.members:
			# check if the contact has a link to the messaging group
			if not frappe.db.exists(
				"Dynamic Link",
				{
					"link_doctype": "Messaging Group",
					"link_name": self.name,
					"parenttype": "Contact",
					"parent": messaging_group_member.contact,
				},
			):
				# add the link to the contact
				frappe.get_doc("Contact", messaging_group_member.contact).append(
					"links",
					{"link_doctype": "Messaging Group", "link_name": self.name},
				).save(ignore_permissions=True)

		# check if the messaging group has a linked email group
		if self.email_group:
			# get the email group members; the sync only adds to them: an Email Group can hold
			# subscribers of its own, so a member who is not in this group is left in place
			email_group_members = frappe.get_all(
				"Email Group Member",
				filters={"email_group": self.email_group},
				fields=["email"],
			)

			# get the contact for each messaging group member
			members_contacts = [
				Contact(
					"Contact",
					messaging_group_member.contact,
					fields=["email_id", "unsubscribed"],
				)
				for messaging_group_member in self.members
			]

			# if the messaging group member is not in the email group, add it
			for contact in members_contacts:
				if contact.email_id and str(contact.email_id).strip().lower() not in [
					str(email_group_member.email).strip().lower()
					for email_group_member in email_group_members
				]:
					EmailGroupMember(
						{
							"doctype": "Email Group Member",
							"email_group": self.email_group,
							"email": contact.email_id,
							"unsubscribed": contact.unsubscribed,
						}
					).insert(ignore_permissions=True, ignore_if_duplicate=True)

	# on trash, remove the link to the messaging group from the associated contacts
	def on_trash(self):
		if not self.members:
			return

		# unlink the messaging group from the associated contacts
		for messaging_group_member in self.members:
			# check if the contact has a link to the messaging group
			self.unlink_contact_from_messaging_group(messaging_group_member.contact)

	def after_delete(self):
		"""Delete the linked Email Group too, when the deleting caller asked for it.

		It runs once this group is gone, so frappe's link check does not count this group's
		link to the Email Group; frappe.delete_doc checks the user's delete permission on it.
		"""
		if self.flags.delete_email_group and self.email_group:
			frappe.delete_doc("Email Group", self.email_group)

	# action function to add contact to "Messaging Group"
	def add_contact(self, contact_name):
		# add the contact to the group
		if not frappe.db.exists(
			"Messaging Group Member",
			{
				"parent": self.name,
				"contact": contact_name,
			},
		):
			self.append("members", {"contact": contact_name})
			self.save(ignore_permissions=True)

	def add_contacts(self, contacts):
		# add the contacts to the group
		for contact in contacts:
			self.add_contact(contact)

	# action function to remove contact from "Messaging Group"
	def remove_contact(self, contact_name):
		# remove the contact from the group
		MessagingGroupMembers = DocType("Messaging Group Member")
		frappe.qb.from_(MessagingGroupMembers).delete().where(
			(MessagingGroupMembers.parent == self.name) & (MessagingGroupMembers.contact == contact_name)
		).run()
		self.notify_update()
		self.unlink_contact_from_messaging_group(contact_name)

	def remove_contacts(self, contacts):
		# remove the contacts from the group
		for contact in contacts:
			self.remove_contact(contact)

	def unlink_contact_from_messaging_group(self, contact_name):
		# check if the contact has a link to the messaging group
		DynamicLinks = DocType("Dynamic Link")
		frappe.qb.from_(DynamicLinks).delete().where(
			(DynamicLinks.link_doctype == "Messaging Group")
			& (DynamicLinks.link_name == self.name)
			& (DynamicLinks.parenttype == "Contact")
			& (DynamicLinks.parent == contact_name)
		).run()
		doc_exists = frappe.db.exists("Contact", contact_name)
		if doc_exists:
			# save the contact to update the links
			frappe.get_doc("Contact", contact_name).notify_update()


@frappe.whitelist(methods=["POST"])
def delete_messaging_groups(names: str | list[str], delete_email_group: bool = False) -> list[str]:
	"""Delete Messaging Groups and, when `delete_email_group` is set, each one's linked Email Group.

	The desk's delete, from the form and from the list, asks whether to delete the linked Email
	Group and calls this with the answer; by default the Email Group is kept. Every permission is
	checked before anything is deleted, and the request is one transaction, so a refusal deletes
	nothing.

	Args:
		names: The Messaging Groups, as a list or a JSON-encoded list.
		delete_email_group: Delete each group's linked Email Group as well.

	Returns:
		The names of the Email Groups that were deleted.
	"""
	group_names: list[str] = json.loads(names) if isinstance(names, str) else list(names)
	also_email_groups = frappe.utils.sbool(delete_email_group)

	email_groups: dict[str, str] = {}
	for name in group_names:
		frappe.has_permission("Messaging Group", "delete", name, throw=True)
		email_group = frappe.db.get_value("Messaging Group", name, "email_group")
		if also_email_groups and email_group:
			frappe.has_permission("Email Group", "delete", email_group, throw=True)
			email_groups[name] = str(email_group)

	for name in group_names:
		frappe.delete_doc(
			"Messaging Group", name, flags=frappe._dict(delete_email_group=name in email_groups)
		)

	if email_groups:
		frappe.msgprint(
			_("Deleted the Email Groups {0} too").format(", ".join(sorted(email_groups.values()))),
			alert=True,
		)
	return sorted(email_groups.values())
