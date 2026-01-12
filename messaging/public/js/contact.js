// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contact", {
	refresh: function (frm) {
		// add a "Add to Group" button to add the contact to a messaging group
		if (frm.doc.creation) {
			frm.add_custom_button(__("Add to Group"), function () {
				frappe.prompt(
					{
						fieldname: "group_name",
						label: "Messaging Group",
						fieldtype: "Link",
						options: "Messaging Group",
						reqd: 1,
					},
					function (data) {
						frm.call({
							doc: frm.doc,
							method: "add_to_group",
							args: {
								group_name: data.group_name,
							},
							freeze: true,
						}).done((r) => {
							frm.reload_doc();
							// frappe.show_alert(r.message).then(() => {
							//     frm.reload_doc();
							// }
							// );
						});
					}
				);
			});
		}
	},
});
