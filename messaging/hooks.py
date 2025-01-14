app_name = "messaging"
app_title = "Messaging"
app_publisher = "Avunu LLC"
app_description = "Messaging functionality for Frappe Sites"
app_email = "mail@avu.nu"
app_license = "mit"

# include js in doctype views
doctype_js = {
    "Contact": "public/js/contact.js",
    "Communication": "public/js/communication.js",
}

doctype_list_js = {"Contact": "public/js/contact_list.js"}

override_doctype_class = {
    "Contact": "messaging.overrides.contact.Contact",
}

doc_events = {
    "Contact": {
        "on_update": "messaging.overrides.contact.add_to_all_contacts_group",
        "validate": "messaging.messaging.hooks.contact.validate",
    }
}


scheduler_events = {
    "all": [
        # "messaging.tasks.all",
        # check every minute for scheduled messages that need to be sent
        "messaging.messaging.doctype.group_text_message.send_scheduled_messages",
    ],
}
