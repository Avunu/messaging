// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

/**
 * @typedef {object} GroupResult What bulk_add_to_group returns.
 * @property {"Success" | "Error"} status
 * @property {string} message
 */

/** @type {frappe.views.ListViewSettings<"Contact">} */
frappe.listview_settings["Contact"] = {
	/** @param {import("frappe-types").ListView} listview frappe passes the list view itself */
	onload: function (listview) {
		listview.page.add_action_item(__("Add to Group"), function () {
			var docnames = listview.get_checked_items();
			if (docnames.length === 0) {
				frappe.throw(__("Please select at least one Contact."));
			}
			// pluck the docnames from the listview
			// and pass them to the server-side method
			const names = docnames.map(function (item) {
				return item.name;
			});
			frappe.prompt(
				{
					fieldname: "group_name",
					label: __("Messaging Group"),
					fieldtype: "Link",
					options: "Messaging Group",
					reqd: 1,
				},
				function (data) {
					frappe.call({
						method: "messaging.messaging.custom.contact.bulk_add_to_group",
						args: {
							doc_names: names,
							group_name: data.group_name,
						},
						callback: function (r) {
							const result = /** @type {GroupResult} */ (r.message);
							if (result.status === "Success") {
								frappe.show_alert({
									message: result.message,
									indicator: "green",
								});
							} else if (result.status === "Error") {
								frappe.show_alert({
									message: result.message,
									indicator: "red",
								});
							} else {
								frappe.throw(result.message);
							}
						},
					});
				},
			);
		});
	},
};
