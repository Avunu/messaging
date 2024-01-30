import json
import frappe
from frappe.contacts.doctype.contact.contact import Contact


class Contact(Contact):
    # action function to add contact to "Messaging Group"
    @frappe.whitelist()
    def add_to_group(self, group_name):
        # add the contact to the group
        mg = frappe.get_doc("Messaging Group", group_name)
        mg.add_contact(self.name)


@frappe.whitelist()
def bulk_add_to_group(doc_names, group_name):
    doc_names = json.loads(doc_names)
    for doc_name in doc_names:
        doc = frappe.get_doc("Contact", doc_name)
        doc.add_to_group(group_name)
    return {
        "status": "Success",
        "message": frappe._("Added contacts to group"),
    }
