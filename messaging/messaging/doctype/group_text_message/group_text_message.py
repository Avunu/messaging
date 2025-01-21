# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils.data import get_datetime, now_datetime


# Define DocTypes for query builder
ContactPhone = DocType("Contact Phone")
MessagingGroupMember = DocType("Messaging Group Member")
Contact = DocType("Contact")


class GroupTextMessage(Document):
    def validate(self):
        # if the delivery_datetime is in the past, throw an error
        if (
            self.schedule
            and self.delivery_datetime
            and get_datetime(self.delivery_datetime) < now_datetime()
        ):
            frappe.throw("Scheduled delivery must be in the future.")
            self.status = "Scheduled"

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
        # get the messaging group
        messaging_groups = [group.messaging_group for group in self.messaging_group]
        excluded_groups = [group.messaging_group for group in self.exclude_groups]

        # Base contact query
        # contact_query = (
        #     frappe.qb.from_(MessagingGroupMember)
        #     .select(MessagingGroupMember.contact)
        #     .where(MessagingGroupMember.parent.isin(messaging_groups))
        #     .where(MessagingGroupMember.parenttype == "Messaging Group")
        # )

        # TODO: make sure this new query works before removing the old one ^^^
        # Base contact query, exclude contacts who do not have sms consent
        contact_query = (
            frappe.qb.from_(MessagingGroupMember)
            .join(Contact)
            .on(Contact.name == MessagingGroupMember.contact)
            .select(MessagingGroupMember.contact)
            .where(MessagingGroupMember.parent.isin(messaging_groups))
            .where(MessagingGroupMember.parenttype == "Messaging Group")
            .where(Contact.consent_sms == 1)
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

        # send the text message to the contact phone numbers
        send_sms(contact_phone_numbers, self.message)

        comment = (
            f"Sent to {len(contact_phone_numbers)} contacts: {', '.join(contact_phone_numbers)}"
        )
        self.add_comment("Info", comment)

        # set the status of the group text message to sent
        self.delivery_datetime = now_datetime()
        self.status = "Sent"
        self.save()
        frappe.db.commit()
