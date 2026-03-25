import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ScrapDispatch(Document):

    def on_submit(self):

        frappe.msgprint("SUBMIT")

        processed = {}

        # ✅ GROUPING (avoid duplicate bug)
        for row in self.table_thrp:

            if not row.scrap_reference:
                continue

            key = (row.scrap_reference, row.item_code)
            processed[key] = processed.get(key, 0) + flt(row.item_qty)

        # ✅ PROCESS
        for (ref, item), qty in processed.items():

            declaration = frappe.get_doc("Scrap Material Declaration", ref)

            for child in declaration.table:

                if child.scrap_item_material_code == item:

                    actual = flt(child.actual_qty)
                    consumed = flt(child.consumed_qty)
                    remaining = actual - consumed

                    if remaining < qty:
                        frappe.throw(
                            f"Not enough remaining qty in {ref}. Available: {remaining}"
                        )

                    # ✅ FIX: SAFE UPDATE
                    child.consumed_qty = consumed + qty

            declaration.save(ignore_permissions=True)

        frappe.db.commit()