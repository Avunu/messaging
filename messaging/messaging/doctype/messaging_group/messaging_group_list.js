// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

const DELETE_GROUPS = "messaging.messaging.doctype.messaging_group.messaging_group.delete_messaging_groups";

/**
 * Ask whether to delete the checked groups' linked Email Groups too, then delete.
 * @param {import("frappe-types").ListView} listview
 */
function confirm_delete(listview) {
	const docs = listview.get_checked_items();
	const names = docs.map((doc) => doc.name);
	const email_groups = docs.map((doc) => doc.email_group).filter(Boolean);
	const dialog = new frappe.ui.Dialog({
		title:
			names.length > 1 ? __("Delete {0} Messaging Groups?", [names.length]) : __("Delete {0}?", [names[0]]),
		fields: [
			{
				fieldtype: "Check",
				fieldname: "delete_email_group",
				label: __("Also delete their linked Email Groups ({0})", [email_groups.join(", ")]),
				default: 0,
				hidden: email_groups.length ? 0 : 1,
			},
		],
		primary_action_label: __("Delete"),
		primary_action: (values) => {
			dialog.hide();
			frappe
				.call({
					method: DELETE_GROUPS,
					args: { names, delete_email_group: email_groups.length && values.delete_email_group ? 1 : 0 },
					freeze: true,
				})
				.then(() => {
					listview.clear_checked_items();
					listview.refresh();
				});
		},
	});
	dialog.show();
}

/** @type {frappe.views.ListViewSettings<"Messaging Group">} */
frappe.listview_settings["Messaging Group"] = {
	add_fields: ["email_group"],
	/** @param {import("frappe-types").ListView} listview frappe passes the list view itself */
	onload(listview) {
		// The list's own Delete action calls frappe's bulk delete, which takes no options, so it is
		// replaced by one that asks about the linked Email Groups and calls delete_messaging_groups.
		const delete_label = __("Delete", null, "Button in list view actions menu");
		const standard_items = listview.get_actions_menu_items.bind(listview);
		listview.get_actions_menu_items = () => {
			const items = standard_items();
			for (const item of items) {
				if (item.standard && item.label === delete_label) item.action = () => confirm_delete(listview);
			}
			return items;
		};
		listview.page.clear_actions_menu();
		listview.set_actions_menu_items();
	},
};
