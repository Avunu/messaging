# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

app_description = "Chat inbox for email and SMS, Twilio group texts and newsletter merge tags"
app_email = "mail@avu.nu"
app_license = "MIT"
app_name = "messaging"
app_publisher = "Avunu LLC"
app_title = "Messaging"

# App includes - Vite-built assets (like frappe_editor pattern)
# Direct /assets/ path bypasses assets.json lookup, cache-busting via build_version query param
app_include_js = [
	"chat.bundle.js",  # Will resolve to /assets/messaging/dist/js/chat.bundle.[hash].js
]
app_include_css = [
	"chat.bundle.css",  # Will resolve to /assets/messaging/dist/css/chat.bundle.[hash].css
]

doc_events = {
	"Communication": {
		"after_insert": "messaging.messaging.api.chat.api.notify_new_communication",
	},
}
doctype_js = {
	"Contact": "public/js/contact.js",
	"Communication": "public/js/communication.js",
}
doctype_list_js = {
	"Contact": "public/js/contact_list.js",
}
export_python_type_annotations = True
extend_doctype_class = {
	"Contact": "messaging.messaging.custom.contact.Contact",
	"Contact Phone": "messaging.messaging.custom.contact_phone.ContactPhone",
	"Newsletter": "messaging.messaging.custom.newsletter.Newsletter",
}
required_apps = ["newsletter"]
send_sms = ["messaging.messaging.api.twilio_sms.send_sms"]
scheduler_events = {
	"all": [
		"messaging.messaging.doctype.group_text_message.send_scheduled_messages",
	],
}

# Install/migrate hooks for doctype view registration
after_install = "messaging.config.after_install"
after_migrate = "messaging.config.after_migrate"
after_uninstall = "messaging.config.after_uninstall"
