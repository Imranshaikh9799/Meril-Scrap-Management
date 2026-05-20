# Copyright (c) 2026, Khan Anish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate, nowdate, now_datetime

class IdleFixedAssetDeclaration(Document):
    
    def before_save(self):

        # ================= FIXED ASSET =================
        if self.scrap_type == "Fixed Asset":
            self.handle_fixed_asset_declare_by()
            return   

    def autoname(self):
        prefix = frappe.db.get_value(
            "Company Master", self.company_name, "prefix"
        )

        if not prefix:
            frappe.throw("Prefix not found in Company Master")

        today = getdate(nowdate())
        year = today.year

        # Financial year calculation (April to March)
        if today.month >= 4:
            fy_start = year
            fy_end = year + 1
        else:
            fy_start = year - 1
            fy_end = year

        self.name = make_autoname(
            f"{prefix}/{fy_start}-{str(fy_end)[-2:]}/.######"
        )
   
    # ==================================================
    # FIXED ASSET → DECLARE BY ONLY ON SEND
    # ==================================================
    def handle_fixed_asset_declare_by(self):

        before = self.get_doc_before_save()
        if not before:
            return

        if (
            before.workflow_state == "Draft"
            and self.workflow_state == "Approval Pending from HOD"
        ):
            self.ensure_stage("Declare By")   

    def upsert_approval_row(self, stage, status):

        full_name = frappe.db.get_value(
            "User", frappe.session.user, "full_name"
        )

        for row in self.approval_details:
            if row.stages == stage:
                row.approved_by = full_name
                row.approved_rejected = status
                row.date = now_datetime()
                return

        self.append("approval_details", {
            "stages": stage,
            "approved_by": full_name,
            "approved_rejected": status,
            "date": now_datetime()
        })
        
    # --------------------------------------------------
    # ENSURE STAGE (FIXED ASSET)
    # --------------------------------------------------
    def ensure_stage(self, stage):

        for row in self.approval_details:
            if row.stages == stage:
                return

        self.append("approval_details", {
            "stages": stage,
            "approved_by": frappe.db.get_value(
                "User", frappe.session.user, "full_name"
            ),
            "approved_rejected": "Approved",
            "date": now_datetime()
        })     
        

# ======================================================
# REMARK BASED APPROVAL (FIXED ASSET) - Updated for new states
# ======================================================
@frappe.whitelist()
def update_approval_remarks(docname, remarks, action):

    if not remarks:
        frappe.throw("Remarks is mandatory")

    doc = frappe.get_doc("Idle Fixed Asset Declaration", docname)

    full_name = frappe.db.get_value(
        "User", frappe.session.user, "full_name"
    )

    # STATUS
    status = "Approved"
    if action == "Reject":
        status = "Rejected"

    # STAGE DETECTION
    if action == "Send":
        stage = "Declare By"
    else:
        state_to_stage_map = {
            "Approval Pending from HOD": "HOD",
            "Approval Pending from R&D Assessment Team": "R&D Assessment Team",
            "Approval Pending from Maintenance Assessment Team Plant": "Maintenance Assessment Team Plant",
            "Approval Pending from Maintenance Assessment Team Plant HOD":"Maintenance Assessment Team Plant HOD",
            "Approval Pending from Maintenance Assessment Team": "Maintenance Assessment Team",
            "Approval Pending from Maintenance Assessment HOD": "Maintenance Assessment HOD",
            "Approval Pending from Mechanical Assessment Team Plant": "Mechanical Assessment Team Plant",
            "Approval Pending from Mechanical Assessment Team Plant HOD": "Mechanical Assessment Team Plant HOD",
            "Approval Pending from Electrical Assessment Team Plant": "Electrical Assessment Team Plant",
            "Approval Pending from Electrical Assessment Team Plant HOD": "Electrical Assessment Team Plant HOD",
            "Approval Pending from BMS Assessment Team Plant": "BMS Assessment Team Plant",
            "Approval Pending from BMS Assessment Team Plant HOD": "BMS Assessment Team Plant HOD",
            "Approval Pending from QC Maintenance Assessment Team Plant": "QC Maintenance Assessment Team Plant",
            "Approval Pending from QC Maintenance Assessment Team Plant HOD": "QC Maintenance Assessment Team Plant HOD",
            "Approval Pending from QC Packing Maintenance Assessment Team Plant": "QC Packing Maintenance Assessment Team Plant",
            "Approval Pending from QC Packing Maintenance Assessment Team Plant HOD": "QC Packing Maintenance Assessment Team Plant HOD",
            "Approval Pending from QA Maintenance Assessment Team Plant": "QA Maintenance Assessment Team Plant",
            "Approval Pending from QA Maintenance Assessment Team Plant HOD": "QA Maintenance Assessment Team Plant HOD",
            "Approval Pending from Office Assessment Team": "Office Assessment Team",
            "Approval Pending from Office Assessment HOD": "Office Assessment HOD",
            "Approval Pending from F & A HOD": "F & A HOD",
            "Approval Pending from Employee Welfare Equipment Assessment Team": "Employee Welfare Equipment Assessment Team",
            "Approval Pending from Employee Welfare Equipment Assessment HOD": "Employee Welfare Equipment Assessment HOD",
            "Approval Pending from F & A Department": "F & A Department",
            "Approval Pending from R&D Assessment HOD": "R&D Assessment HOD",
            "Approval Pending from Assessment Team": "Assessment Team",
            "Approval Pending from IT Assessment Team": "Assessment Team",
            "Approval Pending from IT Assessment HOD": "Assessment HOD",  
            "Approval Pending from Civil Assessment Team": "Assessment Team",
            "Approval Pending from Civil Assessment HOD": "Assessment HOD",  
          "Approval Pending from Vehicles Assessment Team": "Assessment Team",
            "Approval Pending from Vehicles Assessment HOD": "Assessment HOD",   
            "Approval Pending from E&M Assessment Team": "Assessment Team",
            "Approval Pending from E&M Assessment HOD": "Assessment HOD",           
            "Approval Pending from Assessment HOD": "Assessment HOD",
            "Approval Pending from QA / QC Assessment Team": "QA / QC Assessment Team",
            "Approval Pending from QA/QC HOD": "QA / QC Assessment HOD",
            "Approval Pending from CFO": "CFO",
            "Approval Pending from CEO": "CEO",
            "Approve Pending from F & A Dept.": "F & A Dept.",
            "Approve Pending from F & A HOD": "F & A HOD"
        }

        stage = state_to_stage_map.get(doc.workflow_state)

        if not stage:
            frappe.throw(
                f"No approval stage mapped for workflow state: {doc.workflow_state}"
            )

    # UPDATE OR INSERT
    for row in doc.approval_details:
        if row.stages == stage:
            row.remarks = remarks
            row.approved_rejected = status
            row.approved_by = full_name
            row.date = now_datetime()
            break
    else:
        doc.append("approval_details", {
            "stages": stage,
            "remarks": remarks,
            "approved_by": full_name,
            "approved_rejected": status,
            "date": now_datetime()
        })

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return True




# ======================================================
# GET APPROVAL DETAILS (Optional - if you need to fetch details)
# ======================================================
@frappe.whitelist()
def get_approval_details(docname):
    """Get approval details for a scrap declaration"""
    doc = frappe.get_doc("Idle Fixed Asset Declaration", docname)
    return {
        "approval_details": [
            {
                "stage": row.stages,
                "approved_by": row.approved_by,
                "status": row.approved_rejected,
                "date": row.date,
                "remarks": row.remarks
            }
            for row in doc.approval_details
        ]
    }
            
        
        
        
        
        
        
        
           

# @frappe.whitelist()
# def update_approval_remarks(docname, remarks, action="Approve"):

#     if not remarks:
#         frappe.throw("Remarks is mandatory")

#     doc = frappe.get_doc("Idle Fixed Asset Declaration", docname)

#     # ---------------- STATUS ----------------
#     if action == "Approve":
#         status = "Approved"
#     elif action == "Reject":
#         status = "Rejected"
#     elif action == "Send":
#         status = "Send"
#     else:
#         status = "Approved"

#     # ---------------- STAGE DETECTION ----------------

#     if action == "Send":
#         stage = "Declare By"

#     else:
#         state_to_stage_map = {
#             "Approval Pending from HOD": "HOD",
#             "Approval Pending from R&D Assessment Team": "R&D Assessment Team",
#             "Approval Pending from R&D Assessment HOD": "R&D Assessment HOD",
#             "Approval Pending from Assessment Team": "Assessment Team",
#             "Approval Pending from Assessment HOD": "Assessment HOD",
#             "Approval Pending from QA / QC Assessment Team": "QA / QC Assessment Team",
#             "Approval Pending from QA/QC HOD": "QA / QC Assessment HOD",
#             "Approval Pending from CFO": "CFO",
#             "Approval Pending from CEO": "CEO",
#             "Approve Pending from F & A Dept.": "F & A Dept.",
#             "Approve Pending from F & A HOD": "F & A HOD",
#         }

#         stage = state_to_stage_map.get(doc.workflow_state)

#         if not stage:
#             frappe.throw(
#                 f"No approval stage mapped for workflow state: {doc.workflow_state}"
#             )

#     # ---------------- UPDATE OR INSERT ----------------
#     full_name = frappe.db.get_value(
#         "User", frappe.session.user, "full_name"
#     )

#     existing_row = None

#     for row in doc.approval_details:
#         if row.stages == stage:
#             existing_row = row
#             break

#     if existing_row:
#         existing_row.remarks = remarks
#         existing_row.approved_rejected = status
#         existing_row.approved_by = full_name
#         existing_row.date = now_datetime()
#     else:
#         doc.append("approval_details", {
#             "stages": stage,
#             "remarks": remarks,
#             "approved_by": full_name,
#             "approved_rejected": status,
#             "date": now_datetime()
#         })

#     doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return True

