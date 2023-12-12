# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import send_sms


class GroupTextMessage(Document):
	# def validate(self):
		# if the status is sent, don't allow the document to be edited
		# if self.status == "Sent":
		# 	frappe.throw("This document has already been sent and cannot be edited.")
	pass

@frappe.whitelist()
def send_text_message(name):

	# get the group text message
	group_text_message = frappe.get_doc("Group Text Message", name)

	# handle scheduled delivery
	if group_text_message.scheduled_delivery:
		# set the status of the group text message to scheduled if it isn't already
		if group_text_message.status != "Scheduled":
			group_text_message.status = "Scheduled"
			group_text_message.save()
		# if the scheduled_delivery datetime is in the future, return success and don't send the text message
		if group_text_message.scheduled_delivery > frappe.utils.now_datetime():
			return "success"

	# get the messaging group
	messaging_group = frappe.get_doc("Messaging Group", group_text_message.messaging_group)

	# use an sql query to get the primary mobile number for every contact in the messaging group
	contact_phone_numbers = frappe.db.sql_list(f"""
		SELECT phone 
		FROM `tabContact Phone` 
		WHERE parent IN (
			SELECT contact 
			FROM `tabMessaging Group Member` 
			WHERE parent = '{messaging_group.name}' 
			AND parenttype = 'Messaging Group'
		) 
		AND is_primary_mobile_no = 1
	""")

	# send the text message to the contact phone numbers
	send_sms(contact_phone_numbers, group_text_message.message, "Gap Church League")

	# set the status of the group text message to sent
	group_text_message.status = "Sent"
	group_text_message.save()

	# submit the group text message
	group_text_message.submit()

	return "success"

def send_scheduled_messages():
	# get all of the group text messages that are scheduled to be sent where the scheduled_delivery datetime is past or equal to now
	group_text_messages = frappe.db.sql(f"""
		SELECT name FROM `tabGroup Text Message` 
		WHERE scheduled_delivery <= '{frappe.utils.now_datetime()}'
		AND status = 'Scheduled'
	""", as_dict=True)
	for group_text_message in group_text_messages:
		# send the text message
		send_text_message(group_text_message.name)