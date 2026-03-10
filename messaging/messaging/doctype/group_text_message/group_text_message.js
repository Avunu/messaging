// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Group Text Message", {
	refresh: function (frm) {
		// add a custom submit button
		if (frm.doc.docstatus == 0) {
			frm.page.set_primary_action("Schedule/Send", function () {
				frm.savesubmit();
			});
		}
	},
});
