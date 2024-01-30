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
        excluded_groups = [group.messaging_group for group in self.excluded_groups]

        # use query builder to get the primary mobile number for every contact in the messaging group
        contact_phone_numbers = (
            frappe.qb.from_(ContactPhone)
            .select(ContactPhone.phone)
            .where(
                ContactPhone.parent.isin(
                    frappe.qb.from_(MessagingGroupMember)
                    .select(MessagingGroupMember.contact)
                    .where(
                        MessagingGroupMember.parent.isin(messaging_groups)
                        & ~MessagingGroupMember.parent.isin(excluded_groups)
                        & MessagingGroupMember.parenttype == "Messaging Group")
                )
            )
            .where(ContactPhone.is_primary_mobile_no == 1)
        ).run(as_list=True)[0]

        # debug
        frappe.log_error(contact_phone_numbers)

        # send the text message to the contact phone numbers
        # send_sms(contact_phone_numbers, self.message)

        # set the status of the group text message to sent
        self.delivery_datetime = now_datetime()
        self.status = "Sent"
        self.save()
