/**
 * Opportunity Probuild Customizations
 * Adds SMS functionality and address autocomplete
 */

frappe.ui.form.on("Opportunity", {
    refresh: function(frm) {
        // Don't run on new/unsaved forms
        if (frm.is_new()) return;
        
        // Add "Send SMS" button
        frm.add_custom_button(__("Send SMS"), function() {
            probuild_show_sms_dialog(frm);
        }, __("Actions"));
        
        // Load SMS history
        probuild_load_sms_history(frm);
    }
});

function probuild_show_sms_dialog(frm) {
    // Fetch recipient options and templates
    Promise.all([
        frappe.call({
            method: 'probuild.probuild.api.twilio.get_sms_recipient_options_for_opportunity',
            args: { opportunity_name: frm.doc.name }
        }),
        frappe.call({
            method: 'probuild.probuild.api.twilio.get_sms_templates',
            args: { doctype: frm.doctype }
        })
    ]).then(([recipients_r, templates_r]) => {
        let recipient_data = recipients_r.message || { options: [], last_used: "" };
        let recipient_options = recipient_data.options || [];
        let templates = templates_r.message || [];
        
        // Build select options
        let select_options = [{ label: "-- Select Recipient --", value: "" }];
        recipient_options.forEach(opt => {
            select_options.push({ label: opt.label, value: opt.value });
        });
        select_options.push({ label: "Custom Number", value: "__custom__" });
        
        // Default to last used or first option
        let default_phone = recipient_data.last_used || "";
        if (!default_phone && recipient_options.length > 0) {
            default_phone = recipient_options[0].value;
        }
        
        let no_numbers_msg = recipient_options.length === 0 
            ? '<p class="text-muted">No phone numbers found. Add a mobile to the Contact or enter a custom number.</p>'
            : '';
        
        let d = new frappe.ui.Dialog({
            title: __('Send SMS'),
            size: 'large',
            fields: [
                {
                    fieldname: 'recipient_html',
                    fieldtype: 'HTML',
                    options: no_numbers_msg
                },
                {
                    fieldname: 'recipient_select',
                    fieldtype: 'Select',
                    label: __('Select Recipient'),
                    options: select_options,
                    default: default_phone || "__custom__",
                    change: function() {
                        let selected = d.get_value('recipient_select');
                        if (selected === "__custom__") {
                            d.set_value('phone_number', '');
                            d.fields_dict.phone_number.$wrapper.show();
                        } else if (selected) {
                            d.set_value('phone_number', selected);
                            d.fields_dict.phone_number.$wrapper.hide();
                        }
                    }
                },
                {
                    fieldname: 'phone_number',
                    fieldtype: 'Data',
                    label: __('Phone Number'),
                    options: 'Phone',
                    reqd: 1,
                    default: default_phone,
                    description: 'You can edit this number if needed'
                },
                {
                    fieldname: 'template',
                    fieldtype: 'Select',
                    label: __('Use Template'),
                    options: [{ value: '', label: '-- Custom Message --' }].concat(
                        templates.map(t => ({ value: t.name, label: t.template_name }))
                    ),
                    change: function() {
                        let template_name = d.get_value('template');
                        if (template_name) {
                            let template = templates.find(t => t.name === template_name);
                            if (template) {
                                d.set_value('message', template.message);
                            }
                        }
                    }
                },
                {
                    fieldname: 'message',
                    fieldtype: 'Text',
                    label: __('Message'),
                    reqd: 1,
                    description: 'Max 160 characters per SMS segment'
                },
                {
                    fieldname: 'char_count',
                    fieldtype: 'HTML',
                    options: '<div class="text-muted" id="sms-char-count">0 characters</div>'
                }
            ],
            primary_action_label: __('Send SMS'),
            primary_action: function(values) {
                if (!values.phone_number) {
                    frappe.throw(__("Please enter a phone number"));
                    return;
                }
                
                d.hide();
                frappe.show_alert({ message: __('Sending SMS...'), indicator: 'blue' });
                
                frappe.call({
                    method: 'probuild.probuild.api.twilio.send_sms',
                    args: {
                        recipient_number: values.phone_number,
                        message: values.message,
                        linked_doctype: frm.doctype,
                        linked_name: frm.doc.name,
                        contact_name: frm.doc.customer_name || frm.doc.party_name
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({ message: __('SMS sent successfully!'), indicator: 'green' }, 5);
                            probuild_load_sms_history(frm);
                        } else {
                            frappe.msgprint({
                                title: __('SMS Failed'),
                                message: r.message ? r.message.error : __('Unknown error'),
                                indicator: 'red'
                            });
                        }
                    }
                });
            }
        });
        
        // Character counter
        d.fields_dict.message.$input.on('input', function() {
            let len = $(this).val().length;
            let segments = Math.ceil(len / 160) || 1;
            $('#sms-char-count').html(`${len} characters (${segments} SMS segment${segments > 1 ? 's' : ''})`);
        });
        
        // Hide phone field if a recipient is pre-selected
        d.$wrapper.on('shown.bs.modal', function() {
            let selected = d.get_value('recipient_select');
            if (selected && selected !== "__custom__") {
                d.fields_dict.phone_number.$wrapper.hide();
            }
        });
        
        d.show();
    });
}

function probuild_load_sms_history(frm) {
    frappe.call({
        method: 'probuild.probuild.api.twilio.get_sms_history',
        args: {
            doctype: frm.doctype,
            name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let html = '<div class="sms-history">';
                html += '<h6 class="text-muted">Recent SMS Messages</h6>';
                
                r.message.slice(0, 5).forEach(msg => {
                    let direction_icon = msg.direction === 'Outbound' ? '→' : '←';
                    let direction_class = msg.direction === 'Outbound' ? 'text-primary' : 'text-success';
                    let time = frappe.datetime.prettyDate(msg.sent_at);
                    
                    html += `<div class="sms-item mb-2 p-2 border-bottom">
                        <span class="${direction_class}">${direction_icon}</span>
                        <strong>${msg.phone_number}</strong>
                        <span class="text-muted small">(${time})</span>
                        <br><small>${frappe.utils.escape_html(msg.message.substring(0, 100))}${msg.message.length > 100 ? '...' : ''}</small>
                    </div>`;
                });
                
                html += '</div>';
                
                // Add to form sidebar or custom section
                if (!frm.fields_dict.sms_history_html) {
                    // Create a section for SMS history below form
                    $(frm.wrapper).find('.form-message').before(`
                        <div class="frappe-control" data-fieldname="sms_history_section">
                            <div class="form-group">
                                <div class="clearfix"><label class="control-label">SMS History</label></div>
                                <div class="control-value sms-history-container">${html}</div>
                            </div>
                        </div>
                    `);
                } else {
                    $(frm.wrapper).find('.sms-history-container').html(html);
                }
            }
        }
    });
}
