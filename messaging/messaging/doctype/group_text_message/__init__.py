# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

from typing import cast

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Now

from .group_text_message import GroupTextMessage

# Define DocTypes for query builder
GroupTextMessages = DocType("Group Text Message")


def send_scheduled_messages():
	# get all of the group text messages that are scheduled to be sent where the delivery_datetime datetime is past or equal to now
	group_text_messages = (
		frappe.qb.from_(GroupTextMessages)
		.select(GroupTextMessages.name)
		.where(GroupTextMessages.delivery_datetime <= Now())
		.where(GroupTextMessages.docstatus == 1)
		.where(GroupTextMessages.schedule == 1)
		.where(GroupTextMessages.status == "Scheduled")
	).run(pluck="name")

	for group_text_name in group_text_messages:
		# send the text message
		cast(GroupTextMessage, frappe.get_doc("Group Text Message", group_text_name)).send_text_message()
