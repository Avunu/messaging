// Copyright (c) 2024, Avunu LLC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Messaging Settings", {
	refresh(frm) {
		// Show helper text based on VAPID key status
		if (!frm.doc.vapid_public_key) {
			frm.dashboard.set_headline(
				__('Click "Generate VAPID Keys" to enable push notifications.'),
			);
		} else {
			frm.dashboard.set_headline(
				__("VAPID keys are configured. Push notifications are ready."),
			);
		}
	},

	generate_vapid_keys_btn(frm) {
		if (frm.doc.vapid_public_key) {
			frappe.confirm(
				__(
					"This will generate new VAPID keys. Existing push subscriptions will stop working and users will need to re-subscribe. Continue?",
				),
				() => {
					frm.call("generate_vapid_keys").then(() => {
						frm.reload_doc();
					});
				},
			);
		} else {
			frm.call("generate_vapid_keys").then(() => {
				frm.reload_doc();
			});
		}
	},
});
