import frappe
from frappe.utils import get_url_to_form

# ---------------------------------------------------------
# Workflow State → Approval Type Mapping
# ---------------------------------------------------------

WORKFLOW_APPROVAL_TYPE_MAP = {
    "Approval Pending from QA/QC": "QA/QC",
    "Approval Pending from PPIC": "PPIC",
    "Approval Pending from Finance HOD": "Finance HOD",
    "Receiving Pending from Scrap Incharge": "Scrap Incharge",
    "Approval Pending from QA": "QA",
}

# ---------------------------------------------------------
# Main Workflow Hook
# ---------------------------------------------------------

def send_workflow_email(doc, method=None):

    if not doc.workflow_state:
        return
    

    before = doc.get_doc_before_save()

    # -----------------------------------------------------
    # ✅ STOP duplicate triggers (IMPORTANT FIX)
    # -----------------------------------------------------
    if before and before.workflow_state == doc.workflow_state:
        return

    # -----------------------------------------------------
    # ✅ Notify Manager ONLY on first creation
    # -----------------------------------------------------
    if not before:
        notify_reports_to_user(doc)

    # -----------------------------------------------------
    # ACKNOWLEDGEMENT MAIL (ONLY once)
    # -----------------------------------------------------
    if doc.workflow_state == "Received by Scrap Incharge":
        send_acknowledgement_to_declared_user(doc)

    if doc.docstatus == 0 and doc.workflow_state == "Draft":
        return

    # -----------------------------------------------------
    # Final approval mail (ONLY once)
    # -----------------------------------------------------
    if doc.workflow_state == "Receiving Pending from Scrap Incharge":
        notify_declared_user_before_receiving(doc)

    approval_type = WORKFLOW_APPROVAL_TYPE_MAP.get(doc.workflow_state)
    if not approval_type:
        return

    send_to_cost_center_users(doc, approval_type)


# ---------------------------------------------------------
# Notify Reports To User (Manager)
# ---------------------------------------------------------

def notify_reports_to_user(doc):

    if not doc.owner:
        return

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": doc.owner},
        ["name", "reports_to"],
        as_dict=True
    )

    if not employee or not employee.reports_to:
        return

    manager_user = frappe.db.get_value(
        "Employee",
        employee.reports_to,
        "user_id"
    )

    if not manager_user:
        return

    doc_url = get_url_to_form(doc.doctype, doc.name)

    frappe.sendmail(
        recipients=[manager_user],
        subject=f"Scrap Declaration {doc.name} Created",
        message=f"""
        Dear Sir/Madam,<br><br>

        A Scrap Declaration has been created by your team member.<br><br>

        <b>Document:</b> {doc.name}<br>
        <b>Employee:</b> {doc.owner}<br>
        <b>Company:</b> {doc.company_name}<br>
        <b>Cost Center:</b> {doc.cost_center}<br>
        <b>Date:</b> {doc.date_addf}<br><br>

        <a href="{doc_url}"
           style="padding:12px 18px;background:#2490ef;color:#fff;
           text-decoration:none;border-radius:6px;">
           View Scrap Declaration
        </a>
        """,
    )


# ---------------------------------------------------------
# Resolve Users from Approval Table
# ---------------------------------------------------------

def send_to_cost_center_users(doc, approval_type):

    if not doc.cost_center:
        return

    approvals = frappe.get_all(
        "Approval",
        filters={
            "parent": doc.cost_center,
            "parenttype": "Cost Center Master",
            "parentfield": "table_pjgs",
            "approval_type": approval_type,
        },
        fields=["employee_name", "role_enable", "role"],
    )

    users = set()
    manager_user = get_reporting_manager(doc)

    for row in approvals:

        if not row.role_enable and row.employee_name:

            user_id = frappe.db.get_value(
                "Employee",
                row.employee_name,
                "user_id"
            )

            if user_id and frappe.db.exists("User", user_id):
                if user_id != manager_user:
                    users.add(user_id)

        elif row.role_enable and row.role:

            role_users = frappe.get_all(
                "Has Role",
                filters={"role": row.role},
                pluck="parent"
            )

            for u in role_users:
                if frappe.db.get_value("User", u, "enabled") == 1:
                    if u != manager_user:
                        users.add(u)

    if not users:
        return

    for user in users:
        create_notification_log(user, doc)

    send_email(
        recipients=list(users),
        subject=f"Scrap Declaration {doc.name} Pending Approval",
        doc=doc,
    )


# ---------------------------------------------------------
# Helper: Get Reporting Manager
# ---------------------------------------------------------

def get_reporting_manager(doc):

    if not doc.owner:
        return None

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": doc.owner},
        ["reports_to"],
        as_dict=True
    )

    if not employee or not employee.reports_to:
        return None

    return frappe.db.get_value(
        "Employee",
        employee.reports_to,
        "user_id"
    )


# ---------------------------------------------------------
# Notification Log
# ---------------------------------------------------------

def create_notification_log(user, doc):

    if not frappe.db.exists("User", user):
        return

    frappe.get_doc({
        "doctype": "Notification Log",
        "subject": f"Scrap Declaration {doc.name} Pending Approval",
        "email_content": f"""
            A Scrap Declaration is pending for your approval.<br><br>
            <b>Document:</b> {doc.name}<br>
            <b>Cost Center:</b> {doc.cost_center}
        """,
        "for_user": user,
        "type": "Alert",
        "document_type": doc.doctype,
        "document_name": doc.name,
    }).insert(ignore_permissions=True)


# ---------------------------------------------------------
# Approval Email
# ---------------------------------------------------------

def send_email(recipients, subject, doc):

    doc_url = get_url_to_form(doc.doctype, doc.name)

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=f"""
        Dear User,<br><br>

        A <b>Scrap Declaration</b> is pending for your approval.<br><br>

        <b>Document:</b> {doc.name}<br>
        <b>Company:</b> {doc.company_name}<br>
        <b>Cost Center:</b> {doc.cost_center}<br>
        <b>Date:</b> {doc.date_addf}<br>
        <b>Workflow State:</b> {doc.workflow_state}<br><br>

        <a href="{doc_url}"
           style="padding:12px 18px;background:#2490ef;color:#fff;
           text-decoration:none;border-radius:6px;">
           Open Scrap Declaration
        </a>
        """,
    )


# ---------------------------------------------------------
# FINAL APPROVAL MAIL
# ---------------------------------------------------------

def notify_declared_user_before_receiving(doc):

    if not doc.owner:
        return

    frappe.sendmail(
        recipients=[doc.owner],
        subject=f"Scrap Declaration {doc.name} Approved – Pending Receiving",
        message=f"""
        Dear User,<br><br>

        Your Scrap Declaration <b>{doc.name}</b> has been approved and
        is pending scrap receiving.
        """,
    )


# ---------------------------------------------------------
# ACKNOWLEDGEMENT MAIL
# ---------------------------------------------------------

def send_acknowledgement_to_declared_user(doc):

    if not doc.owner:
        return

    frappe.sendmail(
        recipients=[doc.owner],
        subject=f"Scrap Declaration {doc.name} Successfully Received",
        message=f"""
        Dear User,<br><br>

        Your Scrap Declaration <b>{doc.name}</b>
        has been <b>successfully received</b> at {doc.place} by Scrap Incharge.<br><br>

        Thank you.
        """,
    )