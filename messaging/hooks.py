app_description = "Additional messaging functionality for Frappe Sites"
app_email = "mail@avu.nu"
app_license = "mit"
app_name = "messaging"
app_publisher = "Avunu LLC"
app_title = "Messaging"
doc_events = {
    "Contact": {
        "on_update": "messaging.overrides.contact.add_to_all_contacts_group",
        "validate": "messaging.messaging.hooks.contact.validate",
    }
}
doctype_js = {
    "Contact": "public/js/contact.js",
    "Communication": "public/js/communication.js",
}
doctype_list_js = {"Contact": "public/js/contact_list.js"}
export_python_type_annotations = True
override_doctype_class = {
    "Contact": "messaging.overrides.contact.Contact",
    "Newsletter": "messaging.overrides.newsletter.Newsletter",
}
scheduler_events = {
    "all": [
        "messaging.messaging.doctype.group_text_message.send_scheduled_messages",
    ],
}