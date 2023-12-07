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

	return "success"