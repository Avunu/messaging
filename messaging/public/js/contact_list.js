// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

frappe.listview_settings["Contact"] = {
	onload: function (listview) {
		listview.page.add_action_item(__("Add to Group"), function () {
			var docnames = listview.get_checked_items();
			if (docnames.length === 0) {
				frappe.throw("Please select at least one Contact.");
			}
			// pluck the docnames from the listview
			// and pass them to the server-side method
			docnames = docnames.map(function (item) {
				return item.name;
			});
			frappe.prompt(
				{
					fieldname: "group_name",
					label: "Messaging Group",
					fieldtype: "Link",
					options: "Messaging Group",
					reqd: 1,
				},
				function (data) {
					frappe.call({
						method: "messaging.messaging.custom.contact.bulk_add_to_group",
						args: {
							doc_names: docnames,
							group_name: data.group_name,
						},
						callback: function (r) {
							if (r.message.status === "Success") {
								frappe.show_alert({
									message: r.message.message,
									indicator: "green",
								});
							} else if (r.message.status === "Error") {
								frappe.show_alert({
									message: r.message.message,
									indicator: "red",
								});
							} else {
								frappe.throw(r.message.message);
							}
						},
					});
				},
			);
		});
	},
};
