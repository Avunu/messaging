import frappe
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.query_builder import DocType
from frappe.query_builder.functions import Now

# Define DocTypes for query builder
ContactPhone = DocType("Contact Phone")
MessagingGroupMember = DocType("Messaging Group Member")
GroupTextMessage = DocType("Group Text Message")


class GroupTextMessage(Document):
    def validate(self):
        # if the scheduled_delivery is in the past, throw an error
        if (
            self.scheduled_delivery
            and self.scheduled_delivery < frappe.utils.now_datetime()
        ):
            frappe.throw("Scheduled delivery must be in the future.")
            self.status = "Scheduled"

    def on_submit(self):
        # if the group text message is scheduled, don't send it
        if self.schedule:
            self.status = "Scheduled"

        # if the group text message is not scheduled, send it
        else:
            self.send_text_message()

    def on_cancel(self):
        # if the group text message is scheduled, set the status to draft
        if self.schedule:
            self.status = "Draft"

    @frappe.whitelist()
    def send_text_message(self):
        # handle scheduled delivery
        if self.scheduled_delivery:
            # set the status of the group text message to scheduled if it isn't already
            if self.status != "Scheduled":
                self.status = "Scheduled"
                self.save()
            # if the scheduled_delivery datetime is in the future, return success and don't send the text message
            if self.scheduled_delivery > frappe.utils.now_datetime():
                return "success"

        # get the messaging group
        messaging_groups = [group.messaging_group for group in self.messaging_group]

        # use query builder to get the primary mobile number for every contact in the messaging group
        contact_phone_numbers = (
            frappe.qb.from_(ContactPhone)
            .select(ContactPhone.phone)
            .where(
                ContactPhone.parent.isin(
                    frappe.qb.from_(MessagingGroupMember)
                    .select(MessagingGroupMember.contact)
                    .where(MessagingGroupMember.parent.isin(messaging_groups))
                    .where(MessagingGroupMember.parenttype == "Messaging Group")
                )
            )
            .where(ContactPhone.is_primary_mobile_no == 1)
        ).run(as_list=True)[0]

        # send the text message to the contact phone numbers
        send_sms(contact_phone_numbers, self.message)

        # set the status of the group text message to sent
        self.status = "Sent"
        self.save()


def send_scheduled_messages():
    # get all of the group text messages that are scheduled to be sent where the scheduled_delivery datetime is past or equal to now
    group_text_messages = (
        frappe.qb.from_(GroupTextMessage)
        .select(GroupTextMessage.name)
        .where(GroupTextMessage.scheduled_delivery <= Now())
        .where(GroupTextMessage.status == "Scheduled")
    ).run(as_list=True)[0]

    for group_text_name in group_text_messages:
        # send the text message
        frappe.get_doc(
            "Group Text Message", group_text_name["name"]
        ).send_text_message()
