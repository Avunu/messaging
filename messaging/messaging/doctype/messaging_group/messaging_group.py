# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MessagingGroup(Document):
	def on_update(self):
		# if the email group exists, update it
		if frappe.db.exists("Email Group", self.email_group):
			email_group_members = frappe.get_all("Email Group Member", filters={"email_group": self.email_group}, fields=["name"])
			
		# otherwise, create a new one
		else:
			email_group = frappe.new_doc("Email Group")
			email_group.name = self.email_group
			email_group.save()