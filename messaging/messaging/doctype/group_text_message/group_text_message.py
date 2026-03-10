# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils.data import get_datetime, now_datetime

from messaging.messaging.api.twilio_sms import send_sms

# Define DocTypes for query builder
ContactPhone = DocType("Contact Phone")
MessagingGroupMember = DocType("Messaging Group Member")
Contact = DocType("Contact")


class GroupTextMessage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from messaging.messaging.doctype.group_text_messaging_group.group_text_messaging_group import (
			GroupTextMessagingGroup,
		)

		amended_from: DF.Link | None
		delivery_datetime: DF.Datetime | None
		exclude_groups: DF.TableMultiSelect[GroupTextMessagingGroup]
		message: DF.LongText
		message_title: DF.SmallText
		messaging_group: DF.TableMultiSelect[GroupTextMessagingGroup]
		schedule: DF.Check
		status: DF.Literal["Draft", "Sent", "Scheduled", "Error"]
	# end: auto-generated types

	def validate(self):
		# if the delivery_datetime is in the past, throw an error
		if (
			self.schedule
			and self.delivery_datetime
			and (get_datetime(self.delivery_datetime) or now_datetime()) < now_datetime()
		):
			frappe.throw("Scheduled delivery must be in the future.")
			self.status = "Scheduled"

	def after_insert(self):
		if frappe.flags.in_web_form:
			self.submit()

	def on_submit(self):
		# if the group text message is scheduled, don't send it
		if self.schedule:
			self.status = "Scheduled"
			self.save()

		# if the group text message is not scheduled, send it
		else:
			self.send_text_message()

	def on_cancel(self):
		# if the group text message is scheduled, set the status to draft
		if self.schedule:
			self.status = "Draft"

	@frappe.whitelist()
	def send_text_message(self):
		assert isinstance(self.name, str), "Expected self.name to be a string"
		try:
			# get the messaging group
			messaging_groups = [group.messaging_group for group in self.messaging_group]
			excluded_groups = [group.messaging_group for group in self.exclude_groups]

			# Base contact query, exclude contacts who do not have sms consent
			contact_query = (
				frappe.qb.from_(MessagingGroupMember)
				.join(Contact)
				.on(Contact.name == MessagingGroupMember.contact)
				.select(MessagingGroupMember.contact)
				.where(MessagingGroupMember.parent.isin(messaging_groups))
				.where(MessagingGroupMember.parenttype == "Messaging Group")
				.where(Contact.consent_sms == 1)
				.where(Contact.unsubscribed == 0)
			)

			# Conditionally add exclusion
			if excluded_groups:
				contacts_in_excluded_groups_query = (
					frappe.qb.from_(MessagingGroupMember)
					.select(MessagingGroupMember.contact)
					.where(MessagingGroupMember.parent.isin(excluded_groups))
					.where(MessagingGroupMember.parenttype == "Messaging Group")
				)
				contact_query = contact_query.where(
					MessagingGroupMember.contact.notin(contacts_in_excluded_groups_query)
				)

			# Finalize the phone number query
			contact_phone_numbers_query = (
				frappe.qb.from_(ContactPhone)
				.select(ContactPhone.phone)
				.where(ContactPhone.parent.isin(contact_query))
				.where(ContactPhone.is_primary_mobile_no == 1)
				.where(ContactPhone.is_valid == 1)  # Only send to validated numbers (Twilio)
			)

			contact_phone_numbers = contact_phone_numbers_query.run(pluck="phone")

			if not contact_phone_numbers:
				self.add_comment("Info", "No eligible recipients found.")
				self.status = "Error"
				self.save()
				return

			# Send via Twilio with per-recipient error handling
			result = send_sms(contact_phone_numbers, self.message, success_msg=False)

			success = result["success"]
			errors = result["errors"]

			# Build detailed comment
			parts = []
			if success:
				parts.append(
					f"Sent to {len(success)} of {len(contact_phone_numbers)} recipients: {', '.join(success)}"
				)
			if errors:
				error_lines = []
				for err in errors:
					code = err.get("code", "unknown")
					number = err.get("number", "unknown")
					error_lines.append(f"{number} (error {code})")
				parts.append(f"Failed for {len(errors)} recipients: {', '.join(error_lines)}")

			self.add_comment("Info", "<br>".join(parts))

			# set the status of the group text message
			self.delivery_datetime = now_datetime()
			self.status = "Sent" if success else "Error"
			self.save()
			frappe.db.commit()

		except Exception as e:
			frappe.log_error(title="Error sending group text message", message=str(e))
			self.add_comment("Bot", f"Error sending message: {e}")
			frappe.db.set_value("Group Text Message", self.name, "status", "Error")
