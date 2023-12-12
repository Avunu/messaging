// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Group Text Message", {
    onload: function(frm) {
        // check if there is not already a send button and if the form is not already 'sent'
        if (!document.getElementById("send") && frm.doc.status !== "Sent" && frm.doc.status !== "Scheduled") {
            render_send_button(frm);
        }
    },
});

function render_send_button(frm) {
    // put a send button in the html before the save button
    const save_button = document.querySelector('[data-label="Save"]');
    const send_button = document.createElement("button");
    send_button.id = "send";
    send_button.className = "btn btn-success btn-sm";
    send_button.innerHTML = "Send";
    save_button.parentNode.insertBefore(send_button, save_button);
}

async function send_text_message() {
    // save the message
    if (cur_frm.is_dirty()) {
        await cur_frm.save();
    }
    // call the send_text_message server side function
    frappe.call({
        method: "messaging.messaging.doctype.group_text_message.group_text_message.send_text_message",
        args: {
            "name": cur_frm.doc.name
        },
        callback: function (r) {
            // refresh the form
            cur_frm.reload_doc();
            // remove the send button
            document.getElementById("send").remove();
        }
    });
}

// event listener for the send button
addEventListener('click', function (e) {
    e.preventDefault();
    if (e.target && e.target.id == 'send') {
        // send the message
        send_text_message();
    }
});