import frappe
from frappe.contacts.doctype.contact.contact import Contact

class Contact(Contact):
	
    # action function to add contact to "Messaging Group"
	@frappe.whitelist()
	def add_to_group(self, group_name):
		# add the contact to the group
		mg = frappe.get_doc("Messaging Group", group_name)
		mg.add_contact(self.name)