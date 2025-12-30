// Probuild Opportunity customizations - SMS Integration

frappe.ui.form.on('Opportunity', {
    refresh: function(frm) {
        if (frm.is_new()) return;
        
        // Add Send SMS button
        frm.add_custom_button(__('Send SMS'), function() {
            show_sms_dialog(frm);
        }, __('Actions'));
        
        // Load and display SMS history
        load_sms_history(frm);
    }
});

function show_sms_dialog(frm) {
    // Get phone from linked prospect
    let phone_number = '';
    
    if (frm.doc.prospect) {
        frappe.db.get_value('Prospect', frm.doc.prospect, 'probuild_mobile', function(r) {
            phone_number = r && r.probuild_mobile ? r.probuild_mobile : '';
            open_sms_dialog(frm, phone_number);
        });
    } else {
        open_sms_dialog(frm, '');
    }
}

function open_sms_dialog(frm, phone_number) {
    // Load templates first
    frappe.call({
        method: 'probuild.probuild.api.twilio.get_sms_templates',
        args: { doctype: frm.doctype },
        callback: function(r) {
            let templates = r.message || [];
            
            let template_options = [''].concat(templates.map(t => t.template_name));
            
            let d = new frappe.ui.Dialog({
                title: __('Send SMS'),
                size: 'large',
                fields: [
                    {
                        fieldname: 'phone_number',
                        fieldtype: 'Data',
                        label: __('Phone Number'),
                        reqd: 1,
                        default: phone_number,
                        options: 'Phone'
                    },
                    {
                        fieldname: 'template',
                        fieldtype: 'Select',
                        label: __('Use Template'),
                        options: template_options,
                        change: function() {
                            let template_name = d.get_value('template');
                            if (template_name) {
                                // Find template and render with values
                                let template = templates.find(t => t.template_name === template_name);
                                if (template) {
                                    let message = render_template(template.message_template, frm);
                                    d.set_value('message', message);
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
                    d.hide();
                    send_sms(values.phone_number, values.message, frm);
                }
            });
            
            // Character counter
            d.fields_dict.message.$input.on('input', function() {
                let len = $(this).val().length;
                let segments = Math.ceil(len / 160) || 1;
                $('#sms-char-count').html(
                    `${len} characters (${segments} SMS segment${segments > 1 ? 's' : ''})`
                );
            });
            
            d.show();
        }
    });
}

function render_template(template, frm) {
    let message = template;
    
    let context = {
        customer_name: '',
        job_nickname: frm.doc.probuild_job_nickname || '',
        opportunity_name: frm.doc.name || '',
        company_name: frappe.defaults.get_default('company') || 'Probuild'
    };
    
    // Get customer name from prospect
    if (frm.doc.prospect) {
        context.customer_name = frm.doc.prospect_name || frm.doc.prospect;
    }
    
    // Replace placeholders
    for (let key in context) {
        message = message.replace(new RegExp('\\{' + key + '\\}', 'g'), context[key]);
    }
    
    return message;
}

function send_sms(phone_number, message, frm) {
    frappe.call({
        method: 'probuild.probuild.api.twilio.send_sms',
        args: {
            phone_number: phone_number,
            message: message,
            linked_doctype: frm.doctype,
            linked_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Sending SMS...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('SMS sent successfully!'),
                    indicator: 'green'
                }, 5);
                // Reload SMS history
                load_sms_history(frm);
            } else {
                frappe.show_alert({
                    message: __('SMS failed: ') + (r.message ? r.message.error : 'Unknown error'),
                    indicator: 'red'
                }, 7);
            }
        }
    });
}

function load_sms_history(frm) {
    frappe.call({
        method: 'probuild.probuild.api.twilio.get_sms_history',
        args: {
            doctype: frm.doctype,
            name: frm.doc.name
        },
        callback: function(r) {
            let history = r.message || [];
            render_sms_history(frm, history);
        }
    });
}

function render_sms_history(frm, history) {
    // Remove existing section
    $(frm.wrapper).find('.sms-history-section').remove();
    
    if (!history.length) return;
    
    let html = `
        <div class="sms-history-section" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h5 style="margin-bottom: 15px; color: #333;">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                SMS History (${history.length})
            </h5>
            <div class="sms-conversation" style="max-height: 300px; overflow-y: auto;">
    `;
    
    history.forEach(function(sms) {
        let is_outbound = sms.direction === 'Outbound';
        let align = is_outbound ? 'right' : 'left';
        let bg_color = is_outbound ? '#d4edda' : '#e2e3e5';
        let time = frappe.datetime.prettyDate(sms.sent_at);
        
        html += `
            <div style="text-align: ${align}; margin-bottom: 10px;">
                <div style="display: inline-block; max-width: 70%; 
                            background: ${bg_color}; padding: 10px 15px; 
                            border-radius: 10px; text-align: left;">
                    <div style="font-size: 11px; color: #666; margin-bottom: 5px;">
                        ${is_outbound ? '→ Sent' : '← Received'} • ${time}
                        ${sms.status === 'Failed' ? '<span style="color: red;">(Failed)</span>' : ''}
                    </div>
                    <div style="word-wrap: break-word;">${frappe.utils.escape_html(sms.message)}</div>
                </div>
            </div>
        `;
    });
    
    html += '</div></div>';
    
    // Add after form
    $(frm.wrapper).find('.form-layout').after(html);
}

