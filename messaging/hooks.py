app_description = "Additional messaging functionality for Frappe Sites"
app_email = "mail@avu.nu"
app_license = "mit"
app_name = "messaging"
app_publisher = "Avunu LLC"
app_title = "Messaging"

# App includes - using built assets from Vite
app_include_js = "/assets/messaging/dist/chat.bundle.iife.js"
app_include_css = "/assets/messaging/dist/chat.css"

doc_events = {
	"Contact": {
		"on_update": "messaging.overrides.contact.add_to_all_contacts_group",
		"validate": "messaging.messaging.hooks.contact.validate",
	},
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
	"Communication": "public/dist/chat.bundle.iife.js",
}
export_python_type_annotations = True
override_doctype_class = {
	"Contact": "messaging.overrides.contact.Contact",
	"Contact Phone": "messaging.overrides.contact_phone.ContactPhone",
	"Newsletter": "messaging.overrides.newsletter.Newsletter",
}
required_apps = ["newsletter"]
scheduler_events = {
	"all": [
		"messaging.messaging.doctype.group_text_message.send_scheduled_messages",
	],
}
