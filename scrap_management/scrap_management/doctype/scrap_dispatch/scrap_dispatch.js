frappe.ui.form.on('Item Scrap Dispatch', {
    scrap: function(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.item_code) {
            frappe.msgprint("Please select Item Code first");
            return;
        }

        let dialog = new frappe.ui.Dialog({
            title: 'Select Scrap Material',
            fields: [
                {
                    fieldname: 'items_html',
                    fieldtype: 'HTML'
                }
            ],
            size: 'large',
            primary_action_label: 'Select',
            primary_action() {

                let selected_items = [];
                let total_qty = 0;

                dialog.$wrapper.find('tbody tr').each(function() {

                    let checkbox = $(this).find('.select_item');
                    let qty_input = $(this).find('.qty_input');

                    if (checkbox.is(':checked')) {

                        let qty = flt(qty_input.val());
                        let max_qty = flt(checkbox.data('maxqty'));

                        if (qty <= 0) {
                            frappe.msgprint("Enter valid qty");
                            return false;
                        }

                        if (qty > max_qty) {
                            frappe.msgprint("Qty cannot exceed available qty");
                            return false;
                        }

                        selected_items.push({
                            parent: checkbox.data('parent'),
                            qty: qty
                        });

                        total_qty += qty;
                    }
                });

                if (!selected_items.length) {
                    frappe.msgprint("Please select at least one row");
                    return;
                }

                // ✅ FIX 1: DO NOT CLEAR FULL TABLE
           
frm.doc.table_thrp = (frm.doc.table_thrp || []).filter(d => {
    return d.dispatch_row_id !== row.name;
});

                // ✅ ADD INTO LOWER TABLE
                selected_items.forEach(d => {
                    let child = frm.add_child("table_thrp");
                    child.item_code = row.item_code;
                    child.scrap_reference = d.parent;
                    child.item_qty = d.qty;
                    child.dispatch_row_id = row.name; 
                });

                frm.refresh_field("table_thrp");

                // ✅ UPDATE TOP ROW
                frappe.model.set_value(cdt, cdn, "item_qty", total_qty);

                let refs = selected_items.map(d => d.parent).join(", ");
                frappe.model.set_value(cdt, cdn, "scrap_reference", refs);

                dialog.hide();
            }
        });

        // 🔥 FETCH DECLARATIONS
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Scrap Material Declaration',
                fields: ['name'],
                filters: { docstatus: 1 },
                limit_page_length: 100
            },
            callback: function(res) {

                let declarations = res.message || [];
                let all_rows = [];

                let promises = declarations.map(d =>
                    frappe.call({
                        method: 'frappe.client.get',
                        args: {
                            doctype: 'Scrap Material Declaration',
                            name: d.name
                        }
                    })
                );

                Promise.all(promises).then(results => {

                    results.forEach(r => {
                        let doc = r.message;

                        (doc.table || []).forEach(child => {

                            if (child.scrap_item_material_code == row.item_code && flt(child.actual_qty) > 0) {

                                let available = flt(child.actual_qty) - flt(child.consumed_qty || 0);

                                if (available > 0) {
                                    all_rows.push({
                                        parent: doc.name,
                                        qty: available
                                    });
                                }
                            }
                        });
                    });

                    if (!all_rows.length) {
                        dialog.fields_dict.items_html.$wrapper.html(
                            `<p style="color:red;">No matching scrap found</p>`
                        );
                        dialog.show();
                        return;
                    }

                    let html = `
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Select</th>
                                    <th>Declaration</th>
                                    <th>Available Qty</th>
                                    <th>Select Qty</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    all_rows.forEach(d => {
                        html += `
                            <tr>
                                <td>
                                    <input type="checkbox" class="select_item"
                                        data-parent="${d.parent}"
                                        data-maxqty="${d.qty}">
                                </td>
                                <td><b>${d.parent}</b></td>
                                <td><b>${d.qty}</b></td>
                                <td>
                                    <input type="number" class="form-control qty_input"
                                        min="0" max="${d.qty}" value="0">
                                </td>
                            </tr>
                        `;
                    });

                    html += `</tbody></table>`;

                    dialog.fields_dict.items_html.$wrapper.html(html);

                    // ✅ AUTO CHECK WHEN QTY ENTERED
                    dialog.$wrapper.find('.qty_input').on('input', function() {
                        let row_el = $(this).closest('tr');
                        let checkbox = row_el.find('.select_item');
                        checkbox.prop('checked', flt($(this).val()) > 0);
                    });

                    // ✅ FIX 2: AUTO FILL FULL QTY WHEN CHECKBOX SELECTED
                    dialog.$wrapper.find('.select_item').on('change', function() {

                        let row_el = $(this).closest('tr');
                        let qty_input = row_el.find('.qty_input');
                        let max_qty = flt($(this).data('maxqty'));

                        if ($(this).is(':checked')) {
                            qty_input.val(max_qty);
                        } else {
                            qty_input.val(0);
                        }
                    });

                    dialog.show();
                });
            }
        });
    }
});