import frappe
import json
import base64
from frappe.utils import get_url_to_form


# =========================================================
# MAIN WORKFLOW FUNCTION
# =========================================================

def send_fixed_asset_workflow_email(doc, method=None):

    # Stop if Draft
    if doc.workflow_state == "Draft":
        return

    # Avoid duplicate trigger
    before = doc.get_doc_before_save()
    if before and before.workflow_state == doc.workflow_state:
        return

    recipients = [doc.owner]
    subject = f"Fixed Asset Declaration {doc.name} - {doc.workflow_state}"

    send_email(recipients, subject, doc)


# =========================================================
# EMAIL FUNCTION (BASE64 INLINE + ATTACHMENTS)
# =========================================================

def send_email(recipients, subject, doc):

    doc_url = get_url_to_form(doc.doctype, doc.name)

    # -------------------------------------------------
    # Dynamic Heading
    # -------------------------------------------------

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

    # -------------------------------------------------
    # LOGO (BASE64 EMBED)
    # -------------------------------------------------

    logo_html = ""

    try:
        logo_file = frappe.get_doc("File", {"file_url": "/files/logo.png"})
        logo_content = logo_file.get_content()
        logo_base64 = base64.b64encode(logo_content).decode("utf-8")

        logo_html = f"""
        <img src="data:image/png;base64,{logo_base64}" height="60">
        """
    except Exception:
        pass

    attachments = []

    # -------------------------------------------------
    # START HTML
    # -------------------------------------------------

    message = f"""
    <div style="font-family:Arial; font-size:13px;">

    <table width="100%">
        <tr>
            <td style="font-weight:bold;">SOP-MG-IA-MFANR</td>
            <td style="text-align:right;">
                {logo_html}
            </td>
        </tr>
    </table>

    <div style="text-align:center; font-size:18px; font-weight:bold; margin-top:10px;">
        Declaration for Fixed Asset working condition and usefulness
        <br>{sub_heading}
    </div>

    <br>
    """

    # -------------------------------------------------
    # DOCUMENT INFO
    # -------------------------------------------------

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
        <tr>
            <td><b>Cost Center</b></td>
            <td>{doc.cost_center or ""}</td>
            <td><b>Location</b></td>
            <td>{doc.place or ""}</td>
        </tr>
    </table>

    <br>
    """

    # -------------------------------------------------
    # ASSET TABLE
    # -------------------------------------------------

    message += """
    <b>Asset Details</b>
    <table border="1" cellpadding="6" cellspacing="0" width="100%" style="border-collapse:collapse;">
        <tr>
            <th>Images</th>
            <th>Asset Code</th>
            <th>Description</th>
            <th>Qty</th>
            <th>Location</th>
            <th>Tag No</th>
            <th>Reason</th>
        </tr>
    """

    if hasattr(doc, "asset_details"):

        for row in doc.asset_details:

            image_html = ""

            if row.images:
                try:
                    images = json.loads(row.images)

                    for img in images:

                        file_doc = frappe.get_doc("File", {"file_url": img})

                        if file_doc:

                            file_content = file_doc.get_content()

                            encoded = base64.b64encode(file_content).decode("utf-8")

                            image_html += f"""
                            <img src="data:image/png;base64,{encoded}"
                                 height="70"
                                 style="margin:2px;">
                            """

                            # Also attach image
                            attachments.append({
                                "fname": file_doc.file_name,
                                "fcontent": file_content
                            })

                except Exception:
                    pass

            message += f"""
            <tr>
                <td>{image_html}</td>
                <td>{row.asset_code or ""}</td>
                <td>{row.asset_description or ""}</td>
                <td>{row.asset_qty or ""}</td>
                <td>{row.asset_location or ""}</td>
                <td>{row.asset_tag_no or ""}</td>
                <td>{row.reason or ""}</td>
            </tr>
            """

    message += f"""
    </table>

    <br>

    <b>Internal Assessment</b>
    <table border="1" cellpadding="6" cellspacing="0" width="100%" style="border-collapse:collapse;">
        <tr>
            <td><b>Condition</b></td>
            <td>{doc.usable_type or ""}</td>
        </tr>
        <tr>
            <td><b>Workflow Status</b></td>
            <td>{doc.workflow_state or ""}</td>
        </tr>
    </table>

    <br><br>

    <div style="text-align:center;">
        <a href="{doc_url}"
           style="padding:12px 18px;background:#2490ef;color:#fff;
           text-decoration:none;border-radius:6px;">
           Open Document
        </a>
    </div>

    </div>
    """

    # -------------------------------------------------
    # SEND MAIL
    # -------------------------------------------------

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=attachments
    )
