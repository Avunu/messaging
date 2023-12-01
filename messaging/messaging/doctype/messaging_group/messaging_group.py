# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
import datetime
from frappe.model.document import Document


class MessagingGroup(Document):
	def on_update(self):

		# check if the messaging group has a linked email group
		if self.email_group:

			# get the messaging group members
			messaging_group_members = self.members
			# get the contact for each messaging group member
			messaging_group_members_contacts = [frappe.get_doc("Contact", messaging_group_member.contact, fields=['*']) for messaging_group_member in messaging_group_members]

			# create the email group if it doesn't exist
			if not frappe.db.exists("Email Group", self.name):
				email_group = frappe.new_doc("Email Group")
				email_group.name = self.name
				email_group.save()

			# get the email group members
			email_group_members = frappe.get_all("Email Group Member", filters={"email_group": self.name}, fields=["*"])
			# compare the email group members to the messaging group members
			for email_group_member in email_group_members:
				# if the email group member is not in the messaging group, delete it
				if email_group_member.email not in [messaging_group_member.email_id for messaging_group_member in messaging_group_members_contacts]:
					frappe.delete_doc("Email Group Member", email_group_member.name)
			# if the messaging group member is not in the email group, add it
			for messaging_group_member in messaging_group_members_contacts:
				if messaging_group_member.email_id not in [email_group_member.email for email_group_member in email_group_members]:
					email_group_member = frappe.new_doc("Email Group Member")
					email_group_member.email_group = self.name
					email_group_member.email = messaging_group_member.email_id
					email_group_member.unsubscribed = messaging_group_member.unsubscribed
					email_group_member.save()

##############################################################################################################

		messaging_group_example = {
			'name': 'Test',
			'owner': 'wengersc@gmail.com',
			'creation': datetime.datetime(2023, 11, 29, 12, 11, 56, 963093),
			'modified': datetime.datetime(2023, 11, 30, 11, 0, 1, 632708),
			'modified_by': 'wengersc@gmail.com',
			'docstatus': 0,
			'idx': 0,
			'title': 'Test',
			'doctype': 'Messaging Group',
			'members': [
				{'name': 'a1f6ac1862',
				'owner': 'wengersc@gmail.com',
				'creation': datetime.datetime(2023, 11, 29, 12, 11, 56, 963093),
				'modified': datetime.datetime(2023, 11, 30, 11, 0, 1, 632708),
				'modified_by': 'wengersc@gmail.com',
				'docstatus': 0,
				'idx': 1,
				'contact': 'Corin Wenger',
				'parent': 'Test',
				'parentfield': 'members',
				'parenttype': 'Messaging Group',
				'doctype': 'Messaging Group Member'}
			]
		}

		email_group_member_example = {
			'name': '6c99c581cf',
			'creation': datetime.datetime(2023, 11, 30, 11, 3, 44, 275118),
			'modified': datetime.datetime(2023, 11, 30, 11, 3, 44, 275118),
			'modified_by': 'wengersc@gmail.com',
			'owner': 'wengersc@gmail.com',
			'docstatus': 0,
			'idx': 0,
			'email_group': 'Test',
			'email': 'wengersc+testuser@gmail.com',
			'unsubscribed': 0,
			'_user_tags': None,
			'_comments': None,
			'_assign': None,
			'_liked_by': None
		}

		contact_example = {
			'name': 'Corin Wenger',
			'owner': 'Administrator',
			'creation': datetime.datetime(2023, 11, 29, 10, 24, 15, 474218),
			'modified': datetime.datetime(2023, 11, 29, 10, 25, 11, 405112),
			'modified_by': 'Administrator',
			'docstatus': 0,
			'idx': 4,
			'first_name': 'Corin',
			'middle_name': None,
			'last_name': 'Wenger',
			'full_name': 'Corin Wenger',
			'email_id': 'wengersc@gmail.com',
			'user': 'wengersc@gmail.com',
			'address': None,
			'sync_with_google_contacts': 0,
			'status': 'Passive',
			'salutation': None,
			'designation': None,
			'gender': None,
			'phone': '',
			'mobile_no': '+16147212006',
			'company_name': None,
			'image': '',
			'google_contacts': None,
			'google_contacts_id': None,
			'pulled_from_google_contacts': 0,
			'is_primary_contact': 0,
			'department': None,
			'unsubscribed': 0,
			'doctype': 'Contact',
			'links': [],
			'phone_nos': [
				{'name': 'bd5d8804ca',
				'owner': 'Administrator',
				'creation': datetime.datetime(2023, 11, 29, 10, 24, 15, 474218),
				'modified': datetime.datetime(2023, 11, 29, 10, 25, 11, 405112),
				'modified_by': 'Administrator',
				'docstatus': 0,
				'idx': 1,
				'phone': '+16147212006',
				'is_primary_phone': 0,
				'is_primary_mobile_no': 1,
				'parent': 'Corin Wenger',
				'parentfield': 'phone_nos',
				'parenttype': 'Contact',
				'doctype': 'Contact Phone'}
			],
			'email_ids': [
				{'name': 'a570749cdf',
				'owner': 'Administrator',
				'creation': datetime.datetime(2023, 11, 29, 10, 24, 15, 474218),
				'modified': datetime.datetime(2023, 11, 29, 10, 25, 11, 405112),
				'modified_by': 'Administrator',
				'docstatus': 0,
				'idx': 1,
				'email_id': 'wengersc@gmail.com',
				'is_primary': 1,
				'parent': 'Corin Wenger',
				'parentfield': 'email_ids',
				'parenttype': 'Contact',
				'doctype': 'Contact Email'}
			]
		}