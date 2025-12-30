from __future__ import annotations

import frappe


def validate_opportunity_centric_flow():
    """
    Validate the entire Opportunity-centric flow:
    1. Create a Lead (should use default ERPNext naming)
    2. Create 2 Opportunities for the same Lead (each gets MMYY-###-P)
    3. Create a Quotation from one Opportunity (gets MMYY-###-Q1)
    4. Create a Project with base ref (gets MMYY-###-J)
    """
    print("=" * 70)
    print("VALIDATING OPPORTUNITY-CENTRIC PROBUILD FLOW")
    print("=" * 70)
    
    # 1. Create a Lead (should use default ERPNext naming)
    print("\n1. Creating Lead (should use default ERPNext naming)...")
    lead = frappe.get_doc({
        "doctype": "Lead",
        "first_name": "Test",
        "last_name": f"Tradie-{frappe.utils.random_string(4)}",
        "email_id": f"tradie-{frappe.utils.random_string(4)}@test.com",
    })
    lead.insert(ignore_permissions=True)
    print(f"   Lead ID: {lead.name}")
    print(f"   Expected: CRM-LEAD-* format (ERPNext default)")
    assert lead.name.startswith("CRM-LEAD"), f"Lead should use default naming, got: {lead.name}"
    print("   ✓ Lead uses default ERPNext naming")
    
    # 2. Create first Opportunity for this Lead
    print("\n2. Creating first Opportunity (should get MMYY-###-P)...")
    opp1 = frappe.get_doc({
        "doctype": "Opportunity",
        "opportunity_from": "Lead",
        "party_name": lead.name,
        "status": "Open",
    })
    opp1.insert(ignore_permissions=True)
    print(f"   Opportunity 1 ID: {opp1.name}")
    print(f"   Base Ref: {opp1.probuild_base_ref}")
    assert opp1.name.endswith("-P"), f"Opportunity should end with -P, got: {opp1.name}"
    print("   ✓ Opportunity 1 uses MMYY-###-P format")
    
    # 3. Create second Opportunity for the same Lead
    print("\n3. Creating second Opportunity for same Lead (should get different MMYY-###-P)...")
    opp2 = frappe.get_doc({
        "doctype": "Opportunity",
        "opportunity_from": "Lead",
        "party_name": lead.name,
        "status": "Open",
    })
    opp2.insert(ignore_permissions=True)
    print(f"   Opportunity 2 ID: {opp2.name}")
    print(f"   Base Ref: {opp2.probuild_base_ref}")
    assert opp2.name.endswith("-P"), f"Opportunity should end with -P, got: {opp2.name}"
    assert opp1.name != opp2.name, "Each Opportunity should have unique ID"
    print("   ✓ Opportunity 2 uses different MMYY-###-P format")
    
    # 4. Create a Quotation linked to Opportunity 1
    print("\n4. Creating Quotation from Opportunity 1 (should get MMYY-###-Q1)...")
    quote = frappe.get_doc({
        "doctype": "Quotation",
        "quotation_to": "Lead",
        "party_name": lead.name,
        "opportunity": opp1.name,
        "transaction_date": frappe.utils.today(),
        "order_type": "Sales",
    })
    quote.insert(ignore_permissions=True)
    print(f"   Quotation ID: {quote.name}")
    print(f"   Base Ref: {quote.probuild_base_ref}")
    print(f"   Quote Ref: {quote.probuild_quote_ref}")
    assert quote.probuild_base_ref == opp1.probuild_base_ref, "Quotation should inherit base ref from Opportunity"
    assert "-Q" in quote.name, f"Quotation should contain -Q, got: {quote.name}"
    print("   ✓ Quotation inherits base ref and uses Q# format")
    
    # 5. Create a Project with base ref from Opportunity 1
    print("\n5. Creating Project with base ref (should get MMYY-###-J)...")
    
    # Ensure company exists
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    if not company:
        print("   Skipping Project creation - no company exists")
    else:
        project = frappe.get_doc({
            "doctype": "Project",
            "project_name": f"Job {opp1.probuild_base_ref}",
            "company": company,
            "status": "Open",
            "probuild_base_ref": opp1.probuild_base_ref,
            "probuild_milestone_total": 5,
        })
        project.insert(ignore_permissions=True)
        print(f"   Project ID: {project.name}")
        print(f"   Job Ref: {project.probuild_job_ref}")
        print(f"   Milestone Total: {project.probuild_milestone_total}")
        assert project.name.endswith("-J"), f"Project should end with -J, got: {project.name}"
        print("   ✓ Project uses MMYY-###-J format")
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE - ALL CHECKS PASSED")
    print("=" * 70)
    print("\nSummary:")
    print(f"  Lead:          {lead.name} (default ERPNext naming)")
    print(f"  Opportunity 1: {opp1.name} (base ref: {opp1.probuild_base_ref})")
    print(f"  Opportunity 2: {opp2.name} (base ref: {opp2.probuild_base_ref})")
    print(f"  Quotation:     {quote.name} (inherits from Opp 1)")
    if company:
        print(f"  Project:       {project.name} (Job from Opp 1)")
    print("=" * 70)
    
    frappe.db.commit()
    
    return {
        "lead": lead.name,
        "opportunity_1": opp1.name,
        "opportunity_2": opp2.name,
        "quotation": quote.name,
        "project": project.name if company else None,
    }




