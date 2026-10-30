// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

const DELETE_GROUPS = "messaging.messaging.doctype.messaging_group.messaging_group.delete_messaging_groups";

frappe.ui.form.on("Messaging Group", {
	onload(frm) {
		// A group with a linked Email Group asks whether to delete that too; the answer goes
		// to delete_messaging_groups. Without one, frappe's own delete runs as it always has.
		const standard_delete = frm.savetrash.bind(frm);
		frm.savetrash = () => {
			const email_group = frm.doc.email_group;
			if (!email_group) {
				standard_delete();
				return;
			}
			const dialog = new frappe.ui.Dialog({
				title: __("Delete {0}?", [frm.docname]),
				fields: [
					{
						fieldtype: "Check",
						fieldname: "delete_email_group",
						label: __("Also delete its Email Group {0}", [email_group]),
						default: 0,
					},
				],
				primary_action_label: __("Delete"),
				primary_action: (values) => {
					dialog.hide();
					frappe
						.call({
							method: DELETE_GROUPS,
							args: { names: [frm.docname], delete_email_group: values.delete_email_group ? 1 : 0 },
							freeze: true,
						})
						.then(() => {
							frappe.model.remove_from_locals(frm.doctype, frm.docname);
							window.history.back();
						});
				},
			});
			dialog.show();
		};
	},
});
