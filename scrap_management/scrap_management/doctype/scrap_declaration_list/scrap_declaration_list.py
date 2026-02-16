import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate, nowdate, now_datetime


class ScrapDeclarationList(Document):

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------
    def before_save(self):

        # T&C only for NON Fixed Asset
        if self.scrap_type != "Fixed Asset" and not self.check:
            frappe.throw(
                "You must accept the Terms and Conditions before submitting."
            )

        # ================= FIXED ASSET =================
        if self.scrap_type == "Fixed Asset":
            self.handle_fixed_asset_declare_by()
            return

        # ================= NON FIXED ASSET =================
        self.handle_non_fixed_asset_flow()

    # --------------------------------------------------
    # AUTONAME
    # --------------------------------------------------
    def autoname(self):

        prefix = frappe.db.get_value(
            "Company Master", self.company_name, "prefix"
        )
        if not prefix:
            frappe.throw("Prefix not found")

        today = getdate(nowdate())
        year = today.year
        fy_start, fy_end = (
            (year, year + 1) if today.month >= 4 else (year - 1, year)
        )

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

    # ==================================================
    # NON FIXED ASSET → ALL FLOWS
    # ==================================================
    def handle_non_fixed_asset_flow(self):

        before = self.get_doc_before_save()
        if not before:
            return

        from_state = before.workflow_state
        to_state = self.workflow_state

        if from_state == to_state:
            return

        # ---------------- DECLARE ----------------
        if from_state == "Draft" and to_state == "Approval Pending from HOD":
            self.upsert_approval_row("Declare By", "Approved")
            return

        # ---------------- HOD ----------------
        if from_state == "Approval Pending from HOD":
            self.upsert_approval_row("HOD", "Approved")
            return

        # ==================================================
        # REGULAR SCRAP
        # ==================================================
        if self.scrap_type == "Regular Scrap":
            return  # direct Scrap Incharge via workflow

        # ==================================================
        # OTHER THAN REGULAR SCRAP
        # ==================================================
        particulars = (self.particulars or "").strip()

        # ---- With QA/QC ----
        if particulars not in ["Spares", "Consumables (Others)"]:

            if from_state == "Approval Pending from QA/QC":
                self.upsert_approval_row("QA/QC", "Approved")
                return

        # ---- PPIC ----
        if from_state == "Approval Pending from PPIC":
            self.upsert_approval_row("PPIC", "Approved")
            return

        # ---- FINANCE HOD ----
        if from_state == "Approval Pending from Finance HOD":
            self.upsert_approval_row("Finance HOD", "Approved")
            return

    # --------------------------------------------------
    # FINAL SUBMIT → SCRAP INCHARGE
    # --------------------------------------------------
    def before_submit(self):

        if self.scrap_type == "Fixed Asset":
            return

        self.upsert_approval_row("Scrap Incharge", "Approved")

    # --------------------------------------------------
    # SAFE UPSERT
    # --------------------------------------------------
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
def update_approval_remarks(docname, stage, remarks, action="Approve"):

    if not remarks:
        frappe.throw("Remarks is mandatory")

    doc = frappe.get_doc("Scrap Declaration List", docname)

    # Status
    if action == "Approve":
        status = "Approved"
    elif action == "Reject":
        status = "Rejected"
    else:  # Send
        status = "Approved"

    # 🔥 STAGE DETERMINATION
    if action == "Send":
        stage = "Declare By"
    else:
        state_to_stage_map = {
            "Approval Pending from HOD": "HOD",
            "Approval Pending from R&D Assessment Team": "R&D Assessment Team",
            "Approval Pending from R&D Assessment HOD": "R&D Assessment HOD",
            "Approval Pending from Assessment Team": "Assessment Team",
            "Approval Pending from Assessment HOD": "Assessment HOD",
            "Approval Pending from QA / QC Assessment Team": "QA / QC Assessment Team",
            "Approval Pending from QA / QC  Assessment HOD": "QA / QC Assessment HOD",
            "Approval Pending from CFO": "CFO",
            "Approval Pending from CEO": "CEO",
            "Approve Pending from F & A Dept.": "F & A Dept.",
            "Approve Pending from F & A HOD": "F & A HOD"
        }

        stage = state_to_stage_map.get(doc.workflow_state)


        if not stage:
         frappe.throw(f"No approval stage mapped for workflow state: {doc.workflow_state}")


    # 🔄 UPDATE OR INSERT
    for row in doc.approval_details:
        if row.stages == stage:
            row.remarks = remarks
            row.approved_rejected = status
            row.approved_by = frappe.db.get_value(
                "User", frappe.session.user, "full_name"
            )
            row.date = now_datetime()
            break
    else:
        doc.append("approval_details", {
            "stages": stage,
            "remarks": remarks,
            "approved_by": frappe.db.get_value(
                "User", frappe.session.user, "full_name"
            ),
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
    doc = frappe.get_doc("Scrap Declaration List", docname)
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
    