app_description = "Additional messaging functionality for Frappe Sites"
app_email = "mail@avu.nu"
app_license = "mit"
app_name = "messaging"
app_publisher = "Avunu LLC"
app_title = "Messaging"

# App includes - Vite-built assets (like frappe_editor pattern)
# Direct /assets/ path bypasses assets.json lookup, cache-busting via build_version query param
app_include_js = "/assets/messaging/dist/chat.bundle.js"
app_include_css = "/assets/messaging/dist/chat.bundle.css"

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
scheduler_events = {
	"all": [
		"messaging.messaging.doctype.group_text_message.send_scheduled_messages",
	],
}
