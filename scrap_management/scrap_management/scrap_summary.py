import frappe
from frappe.utils import nowdate, add_days, getdate, get_url_to_form, get_url
from collections import defaultdict
import openpyxl
from io import BytesIO


# =========================================================
# GET SCRAP DATA
# =========================================================
def get_scrap_data(from_date, to_date):

    return frappe.get_all(
        "Scrap Material Declaration",
        filters={
            "creation": ["between", [from_date, to_date]],
            "docstatus": ["!=", 2]
        },
        fields=[
            "name",
            "cost_center",
            "owner",
            "creation",
            "company_name"
        ]
    )


# =========================================================
# GET HOD USERS FROM COST CENTER
# =========================================================
def get_hod_users(cost_center):

    hod_rows = frappe.get_all(
        "Employee Details",
        filters={
            "parent": cost_center,
            "parenttype": "Cost Center Master",
            "parentfield": "hod"
        },
        fields=["employee"]
    )

    users = set()

    for row in hod_rows:
        user_id = frappe.db.get_value("Employee", row.employee, "user_id")

        if user_id and frappe.db.exists("User", user_id):
            if frappe.db.get_value("User", user_id, "enabled") == 1:
                users.add(user_id)

    return users


# =========================================================
# WEEKLY SUMMARY (Scheduler Entry)
# =========================================================
def weekly_scrap_summary():
   
    to_date = nowdate()
    from_date = add_days(to_date, -7)

    send_summary(from_date, to_date, "Weekly")


# =========================================================
# MONTHLY SUMMARY (Scheduler Entry)
# =========================================================
def monthly_scrap_summary():

    today = getdate()

    from_date = today.replace(day=1)
    to_date = today

    send_summary(from_date, to_date, "Monthly", attach_excel=True)


# =========================================================
# MAIN ENGINE
# =========================================================
def send_summary(from_date, to_date, label, attach_excel=False):

    records = get_scrap_data(from_date, to_date)

    if not records:
        return

    # -----------------------------------------------------
    # HOD → Cost Center → Docs Mapping
    # -----------------------------------------------------
    hod_map = defaultdict(lambda: defaultdict(list))

    for r in records:
        hod_users = get_hod_users(r.cost_center)

        for user in hod_users:
            hod_map[user][r.cost_center].append(r)

    # -----------------------------------------------------
    # Send Email per HOD
    # -----------------------------------------------------
    for user, cost_centers in hod_map.items():

        total_count = sum(len(docs) for docs in cost_centers.values())

        message = f"""
        Dear Sir/Madam,<br><br>

        <b>{label} Scrap Declaration Summary</b><br>
        Period: {from_date} to {to_date}<br>
        Total Records: <b>{total_count}</b><br><br>
        """

        # ---------------------------------------------
        # Cost Center Wise Tables
        # ---------------------------------------------
        for cc, docs in cost_centers.items():

            message += f"<b>Cost Center: {cc}</b><br><br>"

            message += """
            <table border="1" cellpadding="6" cellspacing="0" 
                   style="border-collapse:collapse;width:100%;">
                <tr style="background-color:#f2f2f2;">
                    <th>Document</th>
                    <th>Created By</th>
                    <th>Date</th>
                </tr>
            """

            for d in docs:
                # ✅ FIX: convert to absolute URL
                url = get_url(get_url_to_form("Scrap Material Declaration", d.name))

                message += f"""
                <tr>
                    <td>
                        <a href="{url}" style="color:#2490ef;text-decoration:none;">
                            {d.name}
                        </a>
                    </td>
                    <td>{d.owner}</td>
                    <td>{d.creation}</td>
                </tr>
                """

            message += "</table><br><br>"

        message += "Regards,<br>ERP System"

        # ---------------------------------------------
        # Excel Attachment (Only for Monthly)
        # ---------------------------------------------
        attachments = None
        if attach_excel:
            attachments = [generate_excel(records)]

        # ---------------------------------------------
        # Send Email
        # ---------------------------------------------
        frappe.sendmail(
            recipients=[user],
            subject=f"{label} Scrap Declaration Summary",
            message=message,
            attachments=attachments
        )
# =========================================================
# EXCEL GENERATOR
# =========================================================
def generate_excel(records):

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scrap Summary"

    # Header Row
    ws.append([
        "Document",
        "Cost Center",
        "Created By",
        "Date",
        "Company"
    ])

    # Data Rows
    for r in records:
        ws.append([
            r.name,
            r.cost_center,
            r.owner,
            str(r.creation),
            r.company_name
        ])

    # Save to memory
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return {
        "fname": "Scrap_Summary.xlsx",
        "fcontent": file_stream.read()
    }