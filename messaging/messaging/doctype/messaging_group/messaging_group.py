# Copyright (c) 2023, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
import datetime
from frappe.model.document import Document
from messaging.messaging.doctype.messaging_group_member.messaging_group_member import MessagingGroupMember
from frappe.email.doctype.email_group_member.email_group_member import EmailGroupMember
from frappe.contacts.doctype.contact.contact import Contact
from typing import Dict, List, Optional

class MessagingGroup(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from messaging.messaging.doctype.messaging_group_member.messaging_group_member import MessagingGroupMember

        email_group: DF.Link | None
        members: DF.TableMultiSelect[MessagingGroupMember]
        title: DF.Data | None
    # end: auto-generated types

    # on validate, unlink any removed contacts from the messaging group
    def validate(self):
        # get the messaging group members from before the update
        previous_members = frappe.get_all(
            "Messaging Group Member",
            filters={"parent": self.name},
            pluck="contact",
        )
        if not previous_members:
            return
        # check for members that were removed
        for previous_member in previous_members:
            if previous_member not in [
                messaging_group_member.contact
                for messaging_group_member in self.members
            ]:
                self.unlink_contact_from_messaging_group(previous_member)

    def on_update(self):
        # if there are no members left, end function
        if not self.members:
            return

        # link the messaging group to the associated contacts
        for messaging_group_member in self.members:
            # check if the contact has a link to the messaging group
            if not frappe.db.exists(
                "Dynamic Link",
                {
                    "link_doctype": "Messaging Group",
                    "link_name": self.name,
                    "parenttype": "Contact",
                    "parent": messaging_group_member.contact,
                },
            ):
                # add the link to the contact
                frappe.get_doc("Contact", messaging_group_member.contact).append(
                    "links",
                    {"link_doctype": "Messaging Group", "link_name": self.name},
                ).save(ignore_permissions=True)

        # check if the messaging group has a linked email group
        if self.email_group:
            # get the email group members
            email_group_members = frappe.get_all(
                "Email Group Member",
                filters={"email_group": self.email_group},
                fields=["email"],
            )

            # get the contact for each messaging group member
            self.members_contacts = [
                Contact("Contact", messaging_group_member.contact, fields=["email_id", "unsubscribed"])
                for messaging_group_member in self.members
            ]

            # compare the email group members to the messaging group members
            for email_group_member in email_group_members:
                # if the email group member is not in the messaging group, delete it
                if email_group_member.email not in [
                    messaging_group_member.email_id
                    for messaging_group_member in self.members_contacts
                ]:
                    frappe.delete_doc("Email Group Member", email_group_member.name, ignore_permissions=True)
            # if the messaging group member is not in the email group, add it
            for contact in self.members_contacts:
                if contact.email_id and contact.email_id not in [
                    email_group_member.email
                    for email_group_member in email_group_members
                ]:
                    email_group_member: EmailGroupMember = EmailGroupMember("Email Group Member")
                    email_group_member.email_group = self.email_group
                    email_group_member.email = contact.email_id
                    email_group_member.unsubscribed = (
                        contact.unsubscribed
                    )
                    email_group_member.save(ignore_permissions=True)

    # on trash, remove the link to the messaging group from the associated contacts
    def on_trash(self):
        # get the messaging group members
        self.members = self.members
        if not self.members:
            return

        # unlink the messaging group from the associated contacts
        for messaging_group_member in self.members:
            # check if the contact has a link to the messaging group
            self.unlink_contact_from_messaging_group(messaging_group_member.contact)

        # check if the messaging group has a linked email group
        if self.email_group:
            # delete the email group
            frappe.delete_doc("Email Group", self.name)

    # action function to add contact to "Messaging Group"
    def add_contact(self, contact_name):
        # add the contact to the group
        if not frappe.db.exists(
            "Messaging Group Member",
            {
                "parent": self.name,
                "contact": contact_name,
            },
        ):
            self.append("members", {"contact": contact_name})
            self.save(ignore_permissions=True)
            
    def add_contacts(self, contacts):
        # add the contacts to the group
        for contact in contacts:
            self.add_contact(contact)

    # action function to remove contact from "Messaging Group"
    def remove_contact(self, contact_name):
        # remove the contact from the group
        mgm_exists = frappe.db.exists(
            "Messaging Group Member",
            {
                "parent": self.name,
                "contact": contact_name,
            },
        )
        if mgm_exists:
            mgm = MessagingGroupMember("Messaging Group Member", mgm_exists)
            self.remove(mgm)
            self.unlink_contact_from_messaging_group(contact_name)
            self.save()
            
    def remove_contacts(self, contacts):
        # remove the contacts from the group
        for contact in contacts:
            self.remove_contact(contact)

    def unlink_contact_from_messaging_group(self, contact_name):
        # check if the contact has a link to the messaging group
        dl = frappe.db.exists(
            "Dynamic Link",
            {
                "link_doctype": "Messaging Group",
                "link_name": self.name,
                "parenttype": "Contact",
                "parent": contact_name,
            },
        )
        if dl:
            # delete the link to the contact
            frappe.delete_doc("Dynamic Link", str(dl))
            frappe.get_doc("Contact", contact_name).notify_update()


def get_messaging_group(group_name: str) -> MessagingGroup:
    # see if the group already exists, where the messaging group id is the group name
    group_exists: Optional[str] = str(frappe.db.exists("Messaging Group", group_name))
    group: MessagingGroup
    if group_exists:
        # get the group
        group = MessagingGroup("Messaging Group", group_name)
    else:
        # create the group
        group = MessagingGroup({
            "doctype": "Messaging Group",
            "title": group_name
        }).insert(ignore_permissions=True)
    return group