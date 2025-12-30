/**
 * Probuild Prospect Client Script
 * 
 * Makes Prospect the primary CRM entry point by emphasizing the 
 * "Create Opportunity" workflow. Prospect is the contact hub,
 * Opportunity is the job prospect.
 */

frappe.ui.form.on("Prospect", {
    refresh: function(frm) {
        // Hide the Leads tab - we don't use Leads in Probuild workflow
        probuild_hide_leads_tab(frm);
        
        if (frm.is_new()) {
            // Show message that they need to save first
            probuild_show_save_first_message(frm);
        } else {
            // Add prominent "New Opportunity" button (not overriding primary action)
            frm.add_custom_button(
                __("New Opportunity"),
                function() {
                    frappe.model.open_mapped_doc({
                        method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
                        frm: frm,
                    });
                }
            );
            
            // Make the button more visible by adding a class
            frm.page.wrapper.find('.btn-secondary:contains("New Opportunity")').removeClass('btn-secondary').addClass('btn-primary-light');
            
            // Show helper text for the Opportunities section
            probuild_show_opportunities_helper(frm);
            
            // Add Send SMS button
            frm.add_custom_button(__('Send SMS'), function() {
                probuild_show_sms_dialog(frm);
            }, __('Actions'));
            
            // Load SMS history
            probuild_load_sms_history(frm);
        }
    },
    
    onload: function(frm) {
        if (frm.is_new()) {
            // When creating a new Prospect, show helpful guidance
            frappe.show_alert({
                message: __("Save the Prospect first, then you can add Addresses, Contacts, and Opportunities."),
                indicator: "blue"
            }, 7);
        }
    }
});


/**
 * Show message to save the Prospect first
 */
function probuild_show_save_first_message(frm) {
    setTimeout(function() {
        // Add message to Address & Contact tab area
        var contacts_tab = frm.get_field("address_html");
        if (contacts_tab && contacts_tab.$wrapper) {
            if (!contacts_tab.$wrapper.find(".probuild-save-first").length) {
                contacts_tab.$wrapper.prepend(`
                    <div class="probuild-save-first alert alert-info">
                        <i class="fa fa-info-circle"></i>
                        <strong>Save this Prospect first</strong> to add Addresses and Contacts.
                    </div>
                `);
            }
        }
    }, 200);
}


/**
 * Hide the Leads tab from Prospect form - Probuild doesn't use Leads
 */
function probuild_hide_leads_tab(frm) {
    // Hide the Leads tab entirely
    setTimeout(function() {
        // Hide by tab name in the nav
        frm.page.wrapper.find('.form-tabs .nav-link').each(function() {
            if ($(this).text().trim() === "Leads") {
                $(this).parent().hide();
            }
        });
        
        // Hide the leads field itself
        if (frm.fields_dict.leads) {
            frm.set_df_property("leads", "hidden", 1);
        }
        
        // Hide the leads_section tab break
        if (frm.fields_dict.leads_section) {
            frm.set_df_property("leads_section", "hidden", 1);
        }
    }, 100);
}


/**
 * Show helper text in the Opportunities section
 */
function probuild_show_opportunities_helper(frm) {
    // If no opportunities yet, show guidance
    if (!frm.doc.opportunities || frm.doc.opportunities.length === 0) {
        setTimeout(function() {
            var opportunities_section = frm.get_field("opportunities");
            if (opportunities_section && opportunities_section.$wrapper) {
                var help_html = `
                    <div class="text-muted small mb-3">
                        <i class="fa fa-info-circle"></i>
                        No opportunities yet. Click <strong>New Opportunity</strong> above to create a job prospect.
                        <br>
                        Use <strong>Job Nickname</strong> (e.g., "Wanneroo Job", "Bayswater") to identify each job for this customer.
                    </div>
                `;
                
                // Only add if not already present
                if (!opportunities_section.$wrapper.find(".probuild-opp-help").length) {
                    opportunities_section.$wrapper.prepend(
                        '<div class="probuild-opp-help">' + help_html + '</div>'
                    );
                }
            }
        }, 500);
    }
}


/**
 * Show SMS dialog for sending messages
 */
function probuild_show_sms_dialog(frm) {
    let phone_number = frm.doc.probuild_mobile || '';
    
    frappe.call({
        method: 'probuild.probuild.api.twilio.get_sms_templates',
        args: { doctype: 'Prospect' },
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
                                let template = templates.find(t => t.template_name === template_name);
                                if (template) {
                                    let message = template.message_template
                                        .replace(/{customer_name}/g, frm.doc.prospect_name || '')
                                        .replace(/{company_name}/g, frappe.defaults.get_default('company') || 'Probuild');
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
                    probuild_send_sms(values.phone_number, values.message, frm);
                }
            });
            
            d.fields_dict.message.$input.on('input', function() {
                let len = $(this).val().length;
                let segments = Math.ceil(len / 160) || 1;
                $('#sms-char-count').html(`${len} characters (${segments} SMS segment${segments > 1 ? 's' : ''})`);
            });
            
            d.show();
        }
    });
}


/**
 * Send SMS via Twilio
 */
function probuild_send_sms(phone_number, message, frm) {
    frappe.call({
        method: 'probuild.probuild.api.twilio.send_sms',
        args: {
            phone_number: phone_number,
            message: message,
            linked_doctype: 'Prospect',
            linked_name: frm.doc.name,
            contact_name: frm.doc.prospect_name
        },
        freeze: true,
        freeze_message: __('Sending SMS...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('SMS sent successfully!'),
                    indicator: 'green'
                }, 5);
                probuild_load_sms_history(frm);
            } else {
                frappe.show_alert({
                    message: __('SMS failed: ') + (r.message ? r.message.error : 'Unknown error'),
                    indicator: 'red'
                }, 7);
            }
        }
    });
}


/**
 * Load and display SMS history
 */
function probuild_load_sms_history(frm) {
    frappe.call({
        method: 'probuild.probuild.api.twilio.get_sms_history',
        args: {
            doctype: 'Prospect',
            name: frm.doc.name
        },
        callback: function(r) {
            let history = r.message || [];
            probuild_render_sms_history(frm, history);
        }
    });
}


/**
 * Render SMS history section
 */
function probuild_render_sms_history(frm, history) {
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
    
    $(frm.wrapper).find('.form-layout').after(html);
}
