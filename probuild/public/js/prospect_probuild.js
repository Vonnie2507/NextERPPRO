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
