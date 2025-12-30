// Probuild SMS Integration
// Adds SMS functionality to Prospect and Opportunity forms

frappe.provide("probuild.sms");

probuild.sms = {
    // Initialize SMS features on a form
    setup: function(frm, phone_field) {
        if (!frm.doc.name || frm.is_new()) return;
        
        // Add Send SMS button
        frm.add_custom_button(__('Send SMS'), function() {
            probuild.sms.show_sms_dialog(frm, phone_field);
        }, __('Actions'));
        
        // Add SMS History section
        probuild.sms.load_sms_history(frm);
    },
    
    // Show SMS sending dialog
    show_sms_dialog: function(frm, phone_field) {
        let phone_number = frm.doc[phone_field] || '';
        
        // Load templates first
        frappe.call({
            method: 'probuild.probuild.api.twilio.get_sms_templates',
            args: { doctype: frm.doctype },
            callback: function(r) {
                let templates = r.message || [];
                
                let d = new frappe.ui.Dialog({
                    title: __('Send SMS'),
                    size: 'large',
                    fields: [
                        {
                            fieldname: 'phone_number',
                            fieldtype: 'Data',
                            label: __('Phone Number'),
                            reqd: 1,
                            default: phone_number
                        },
                        {
                            fieldname: 'template',
                            fieldtype: 'Select',
                            label: __('Use Template'),
                            options: [
                                { value: '', label: 'Custom Message' },
                                ...templates.map(t => ({ 
                                    value: t.name, 
                                    label: t.template_name 
                                }))
                            ],
                            change: function() {
                                let template_name = d.get_value('template');
                                if (template_name) {
                                    // Get template content
                                    let template = templates.find(t => t.name === template_name);
                                    if (template) {
                                        // Replace placeholders with actual values
                                        let message = probuild.sms.render_template(
                                            template.message_template, 
                                            frm
                                        );
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
                    primary_action_label: __('Send'),
                    primary_action: function(values) {
                        d.hide();
                        probuild.sms.send_message(
                            values.phone_number,
                            values.message,
                            frm.doctype,
                            frm.doc.name,
                            frm
                        );
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
    },
    
    // Render template with document values
    render_template: function(template, frm) {
        let message = template;
        
        // Get values from the form
        let context = {
            customer_name: frm.doc.prospect_name || frm.doc.customer_name || '',
            job_nickname: frm.doc.probuild_job_nickname || '',
            opportunity_name: frm.doc.name || '',
            company_name: frappe.defaults.get_default('company') || 'Probuild'
        };
        
        // If this is an Opportunity, get prospect name
        if (frm.doctype === 'Opportunity' && frm.doc.prospect) {
            // The prospect name might be fetched
            context.customer_name = frm.doc.prospect_name || frm.doc.prospect || '';
        }
        
        // Replace placeholders
        for (let key in context) {
            message = message.replace(new RegExp('\\{' + key + '\\}', 'g'), context[key]);
        }
        
        return message;
    },
    
    // Send the SMS
    send_message: function(phone_number, message, doctype, name, frm) {
        frappe.call({
            method: 'probuild.probuild.api.twilio.send_sms',
            args: {
                phone_number: phone_number,
                message: message,
                linked_doctype: doctype,
                linked_name: name
            },
            freeze: true,
            freeze_message: __('Sending SMS...'),
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: __('SMS sent successfully!'),
                        indicator: 'green'
                    });
                    // Reload SMS history
                    probuild.sms.load_sms_history(frm);
                } else {
                    frappe.show_alert({
                        message: __('SMS failed: ') + (r.message ? r.message.error : 'Unknown error'),
                        indicator: 'red'
                    });
                }
            }
        });
    },
    
    // Load and display SMS history
    load_sms_history: function(frm) {
        frappe.call({
            method: 'probuild.probuild.api.twilio.get_sms_history',
            args: {
                doctype: frm.doctype,
                name: frm.doc.name
            },
            callback: function(r) {
                let history = r.message || [];
                probuild.sms.render_sms_history(frm, history);
            }
        });
    },
    
    // Render SMS history in the form
    render_sms_history: function(frm, history) {
        // Remove existing section if any
        $(frm.fields_dict.sms_history_html?.$wrapper).empty();
        
        if (!history.length) {
            return;
        }
        
        let html = `
            <div class="sms-history-section" style="margin-top: 20px;">
                <h5 style="margin-bottom: 15px;">
                    <i class="fa fa-comments"></i> SMS History (${history.length})
                </h5>
                <div class="sms-conversation" style="max-height: 400px; overflow-y: auto;">
        `;
        
        history.forEach(function(sms) {
            let is_outbound = sms.direction === 'Outbound';
            let align = is_outbound ? 'right' : 'left';
            let bg_color = is_outbound ? '#d4edda' : '#e2e3e5';
            let icon = is_outbound ? 'fa-arrow-right' : 'fa-arrow-left';
            let time = frappe.datetime.prettyDate(sms.sent_at);
            
            html += `
                <div style="text-align: ${align}; margin-bottom: 10px;">
                    <div style="display: inline-block; max-width: 70%; 
                                background: ${bg_color}; padding: 10px 15px; 
                                border-radius: 10px; text-align: left;">
                        <div style="font-size: 11px; color: #666; margin-bottom: 5px;">
                            <i class="fa ${icon}"></i>
                            ${is_outbound ? 'Sent' : 'Received'} • ${time}
                            ${sms.status === 'Failed' ? '<span class="text-danger">(Failed)</span>' : ''}
                        </div>
                        <div>${frappe.utils.escape_html(sms.message)}</div>
                    </div>
                </div>
            `;
        });
        
        html += '</div></div>';
        
        // Add to form if there's an HTML field for it, otherwise append to form
        if (frm.fields_dict.sms_history_html) {
            $(frm.fields_dict.sms_history_html.$wrapper).html(html);
        } else {
            // Append after the form
            $(frm.wrapper).find('.form-layout').append(html);
        }
    }
};

// Initialize for Prospect
frappe.ui.form.on('Prospect', {
    refresh: function(frm) {
        probuild.sms.setup(frm, 'probuild_mobile');
    }
});

// Initialize for Opportunity  
frappe.ui.form.on('Opportunity', {
    refresh: function(frm) {
        // Get phone from linked prospect
        if (frm.doc.prospect) {
            frappe.db.get_value('Prospect', frm.doc.prospect, 'probuild_mobile', function(r) {
                if (r && r.probuild_mobile) {
                    frm.doc._prospect_mobile = r.probuild_mobile;
                }
            });
        }
        
        frm.add_custom_button(__('Send SMS'), function() {
            let phone = frm.doc._prospect_mobile || '';
            if (!phone && frm.doc.prospect) {
                frappe.db.get_value('Prospect', frm.doc.prospect, 'probuild_mobile', function(r) {
                    probuild.sms.show_sms_dialog(frm, null);
                    if (r && r.probuild_mobile) {
                        // Set phone in dialog after it opens
                        setTimeout(() => {
                            cur_dialog.set_value('phone_number', r.probuild_mobile);
                        }, 100);
                    }
                });
            } else {
                probuild.sms.show_sms_dialog(frm, '_prospect_mobile');
            }
        }, __('Actions'));
        
        // Load SMS history
        probuild.sms.load_sms_history(frm);
    }
});

