// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Group Text Message", {
//     refresh: function (frm) {
//         // add Send button and if the form is not already 'Scheduled'
//         if (cur_frm.doc.docstatus == 3 && frm.doc.status !== "Scheduled") {
//             frm.add_custom_button(__('Send'), function () {
//                 frm.call({
//                     doc: frm.doc,
//                     method: "send_text_message",
//                     freeze: true,
//                 }).done((r) => {
//                     frappe.show_alert(r.message).then(() => {
//                         frm.reload_doc();
//                     }
//                     );
//                 });
//             }
//             ).removeClass("btn-default").addClass("btn-success");
//         }
//     }
// });