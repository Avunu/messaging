# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Now

# Define DocTypes for query builder
GroupTextMessage = DocType("Group Text Message")


def send_scheduled_messages():
    # get all of the group text messages that are scheduled to be sent where the delivery_datetime datetime is past or equal to now
    group_text_messages = (
        frappe.qb.from_(GroupTextMessage)
        .select(GroupTextMessage.name)
        .where(GroupTextMessage.delivery_datetime <= Now())
        .where(GroupTextMessage.status == "Scheduled")
    ).run(as_list=True)[0]

    for group_text_name in group_text_messages:
        # send the text message
        frappe.get_doc(
            "Group Text Message", group_text_name
        ).send_text_message()
