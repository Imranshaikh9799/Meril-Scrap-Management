import frappe
import json
import base64
from frappe.utils import get_url_to_form


# =========================================================
# MAIN WORKFLOW FUNCTION
# =========================================================

def send_fixed_asset_workflow_email(doc, method=None):
    """
    Triggered on save of Idle Fixed Asset Declaration.
    Sends emails based on workflow state changes, plus an acknowledgment
    to the initiator and Reporting Manager after every transition.
    """
    if not doc.workflow_state:
        return

    before = doc.get_doc_before_save()

    if not before or before.workflow_state == doc.workflow_state:
        return

    # -----------------------------------------------------------------
    # Send acknowledgment to Declare By (owner) and Reporting Manager
    # -----------------------------------------------------------------
    send_acknowledgment_to_initiator_and_manager(doc)

    # -----------------------------------------------------------------
    # State-specific emails
    # -----------------------------------------------------------------
    if doc.workflow_state == "Draft":
        handle_rejection(doc)
        return

    if doc.workflow_state == "Change Storage Location":
        handle_location_change(doc)
        return

    if doc.workflow_state == "Submitted":
        handle_final_submission(doc)
        return

    if "Pending" in doc.workflow_state:
       approval_type = extract_approval_type(doc.workflow_state)

    # HOD ko mail nahi bhejna
    if approval_type == "HOD":
        return

    recipients = get_company_approval_users(doc, approval_type)

    if recipients:
        subject = f"Idle Fixed Asset Declaration {doc.name} - {doc.workflow_state}"
        send_email(recipients, subject, doc)


# =========================================================
# ACKNOWLEDGMENT EMAIL TO INITIATOR AND MANAGER
# =========================================================

def send_acknowledgment_to_initiator_and_manager(doc):
    recipients = set()

    # Owner
    if doc.owner and frappe.db.get_value("User", doc.owner, "enabled"):
        recipients.add(doc.owner)

    # Reporting Manager
    manager_emails = get_reports_to_users(doc)
    recipients.update(manager_emails)

    if recipients:
        subject = f"Acknowledgement: Idle Fixed Asset Declaration {doc.name} moved to {doc.workflow_state}"
        send_email(list(recipients), subject, doc)


# =========================================================
# GET REPORTING MANAGER (reports_to)
# =========================================================

def get_reports_to_users(doc):
    users = set()

    if not doc.owner:
        return []

    # Get employee linked to owner
    employee = frappe.db.get_value("Employee", {"user_id": doc.owner}, "name")

    if not employee:
        return []

    # Get manager
    reports_to = frappe.db.get_value("Employee", employee, "reports_to")

    if reports_to:
        manager_user = frappe.db.get_value("Employee", reports_to, "user_id")

        if manager_user and frappe.db.get_value("User", manager_user, "enabled"):
            users.add(manager_user)

    return list(users)


# =========================================================
# HANDLE REJECTION
# =========================================================

def handle_rejection(doc):
    recipients = set()

    if doc.owner:
        recipients.add(doc.owner)

    if doc.approval_details:
        for row in doc.approval_details:
            if row.approved_rejected == "Approved":
                user_email = frappe.db.get_value(
                    "User", {"full_name": row.approved_by}, "name"
                )
                if user_email:
                    recipients.add(user_email)

    if recipients:
        subject = f"Idle Fixed Asset Declaration {doc.name} - Rejected"
        send_email(list(recipients), subject, doc)


# =========================================================
# HANDLE FINAL SUBMISSION
# =========================================================

def handle_final_submission(doc):
    recipients = set()

    if doc.owner:
        recipients.add(doc.owner)

    if doc.approval_details:
        for row in doc.approval_details:
            if row.approved_rejected == "Approved":
                user_email = frappe.db.get_value(
                    "User", {"full_name": row.approved_by}, "name"
                )
                if user_email:
                    recipients.add(user_email)

    if recipients:
        subject = f"Idle Fixed Asset Declaration {doc.name} - Fully Approved"
        send_email(list(recipients), subject, doc)


# =========================================================
# HANDLE CHANGE STORAGE LOCATION
# =========================================================

def handle_location_change(doc):
    recipients = set()

    if not doc.company_name:
        return

    approvals = frappe.get_all(
        "Approval",
        filters={
            "parent": doc.company_name,
            "parenttype": "Company Master",
            "approval_type": "F & A Dept.",
        },
        fields=["employee_name", "role_enable", "role"],
    )

    for row in approvals:
        if not row.role_enable and row.employee_name:
            user_id = frappe.db.get_value("Employee", row.employee_name, "user_id")
            if user_id and frappe.db.get_value("User", user_id, "enabled"):
                recipients.add(user_id)

        elif row.role_enable and row.role:
            role_users = frappe.get_all(
                "Has Role",
                filters={"role": row.role},
                pluck="parent"
            )
            for user in role_users:
                if frappe.db.get_value("User", user, "enabled"):
                    recipients.add(user)

    if recipients:
        subject = f"Change the Location - {doc.name}"
        send_email(list(recipients), subject, doc)


# =========================================================
# Extract Approval Type
# =========================================================

def extract_approval_type(state):
    if "from" in state:
        return state.split("from")[-1].strip()
    return state


# =========================================================
# COMPANY APPROVAL USERS (NON-HOD)
# =========================================================

def get_company_approval_users(doc, approval_type):
    users = set()

    if not doc.company_name:
        return []

    approvals = frappe.get_all(
        "Approval",
        filters={
            "parent": doc.company_name,
            "parenttype": "Company Master",
            "approval_type": approval_type,
        },
        fields=["employee_name", "role_enable", "role"],
    )

    for row in approvals:
        if not row.role_enable and row.employee_name:
            user_id = frappe.db.get_value("Employee", row.employee_name, "user_id")
            if user_id and frappe.db.get_value("User", user_id, "enabled"):
                users.add(user_id)

        elif row.role_enable and row.role:
            role_users = frappe.get_all(
                "Has Role",
                filters={"role": row.role},
                pluck="parent"
            )
            for user in role_users:
                if frappe.db.get_value("User", user, "enabled"):
                    users.add(user)

    return list(users)


# =========================================================
# EMAIL FUNCTION
# =========================================================

def send_email(recipients, subject, doc):
    if not recipients:
        return

    doc_url = get_url_to_form(doc.doctype, doc.name)

    sub_heading = ""
    if doc.particulars:
        if doc.particulars.startswith("Part 1"):
            sub_heading = "Other than R&D and QA/QC instruments and equipments"
        elif doc.particulars.startswith("Part 2"):
            sub_heading = "R&D Department Instruments and Equipments"
        elif doc.particulars.startswith("Part 3"):
            sub_heading = "QA/QC Department Instruments and Equipments"
        elif doc.particulars.startswith("Part 4"):
            sub_heading = "IT & Other Department Instruments and Equipments"

    logo_html = ""
    try:
        logo_file = frappe.get_doc("File", {"file_url": "/files/logo.png"})
        logo_content = logo_file.get_content()
        logo_base64 = base64.b64encode(logo_content).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" height="60"><br><br>'
    except Exception:
        pass

    attachments = []
    if doc.asset_details:
        for row in doc.asset_details:
            if row.images:
                try:
                    image_list = json.loads(row.images)
                    for file_url in image_list:
                        file_doc = frappe.get_doc("File", {"file_url": file_url})
                        attachments.append({
                            "fname": file_doc.file_name,
                            "fcontent": file_doc.get_content()
                        })
                except Exception:
                    pass

    message = f"""
    <div style="font-family:Arial; font-size:13px;">
    <div style="text-align:center;">
        {logo_html}
        <div style="font-size:18px; font-weight:bold;">
            Declaration for Fixed Asset working condition and usefulness
        </div>
        <div>{sub_heading}</div>
    </div>
    <br>
    """

    message += f"""
    <table border="1" cellpadding="6" cellspacing="0" width="100%" style="border-collapse:collapse;">
        <tr>
            <td><b>Document No</b></td>
            <td>{doc.name}</td>
            <td><b>Date</b></td>
            <td>{doc.date_addf or ""}</td>
        </tr>
        <tr>
            <td><b>Company</b></td>
            <td>{doc.company_name or ""}</td>
            <td><b>Department</b></td>
            <td>{doc.department or ""}</td>
        </tr>
    </table>
    """

    message += f"""
    <br><br>
    <div style="text-align:center;">
        <a href="{doc_url}"
           style="
               padding:12px 20px;
               background:#2490ef;
               color:#ffffff;
               text-decoration:none;
               border-radius:6px;
               font-weight:bold;
               display:inline-block;
           ">
           Open Fixed Asset Declaration
        </a>
     </div>
    </div>
    """
    
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=attachments
    )