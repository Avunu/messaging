app_description = "Additional messaging functionality for Frappe Sites"
app_email = "mail@avu.nu"
app_license = "mit"
app_name = "messaging"
app_publisher = "Avunu LLC"
app_title = "Messaging"
doctype_js = {
	"Contact": "public/js/contact.js",
	"Communication": "public/js/communication.js",
}
doctype_list_js = {"Contact": "public/js/contact_list.js"}
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
