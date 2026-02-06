// Copyright (c) 2025, Avunu LLC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Communication", {
	refresh: function (frm) {
		// add a "Reply" button to send an SMS reply
		if (frm.doc.communication_medium == "SMS") {
			frm.add_custom_button(__("Reply"), function () {
				frappe.prompt(
					{
						fieldname: "message",
						label: "Message",
						fieldtype: "Long Text",
						reqd: 1,
					},
					function (data) {
						frappe.call({
							method: "frappe.core.doctype.sms_settings.sms_settings.send_sms",
							args: {
								receiver_list: [frm.doc.phone_no],
								msg: data.message,
							},
							freeze: true,
						});
					},
				);
			});
		}
	},
});
