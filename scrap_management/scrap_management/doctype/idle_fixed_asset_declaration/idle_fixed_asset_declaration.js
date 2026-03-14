// Copyright (c) 2026, Khan Anish and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Idle Fixed Asset Declaration", {
// 	refresh(frm) {

// 	},
// });
// 
frappe.ui.form.on('Idle Fixed Asset Declaration', {

    company_name(frm) {
        frm.set_value('cost_center', null);
        frm.set_value('place', null);
        apply_cost_center_filter(frm);
    },

    cost_center(frm) {
        if (frm.doc.cost_center && !frm.doc.place) {
            frappe.db.get_value(
                'Cost Center Master',
                frm.doc.cost_center,
                'place'
            ).then(r => {
                if (r?.message?.place) {
                    frm.set_value('place', r.message.place);
                }
            });
        }
    },

    scrap_type(frm) {
        frm.set_value('particulars', null);
        apply_particulars_filter(frm);
    },

   
});



/* ======================================================
   FIXED ASSET APPROVAL MAP (Updated with new states)
====================================================== */

const FIXED_ASSET_APPROVAL_MAP = {
    "Approval Pending from HOD": "HOD",
    "Approval Pending from R&D Assessment Team": "R&D Assessment Team",
    "Approval Pending from R&D Assessment HOD": "R&D Assessment HOD",
    "Approval Pending from Assessment Team": "Assessment Team",
    "Approval Pending from IT Assessment Team": "Assessment Team",
    "Approval Pending from IT Assessment HOD": "Assessment HOD", 
    "Approval Pending from Civil Assessment Team": "Civil Assessment Team",
    "Approval Pending from Civil Assessment HOD": "Civil Assessment HOD",
    "Approval Pending from Vehicles Assessment Team": "Vehicles Assessment Team",
    "Approval Pending from Vehicles Assessment HOD": "Vehicles Assessment HOD", 
    "Approval Pending from Assessment HOD": "Assessment HOD",
    "Approval Pending from QA / QC Assessment Team": "QA / QC Assessment Team",
    "Approval Pending from QA/QC HOD": "QA / QC Assessment HOD",
    "Approval Pending from CFO": "CFO",
    "Approval Pending from CEO": "CEO",
    "Approve Pending from F & A Dept.": "F & A Dept.",
    "Approve Pending from F & A HOD": "F & A HOD"
};


frappe.ui.form.on("Idle Fixed Asset Declaration", {
	refresh(frm) {
		if (frm.__confirm_patched) return;
		frm.__confirm_patched = true;

		const original_confirm = frappe.confirm;

		frappe.confirm = function (message, yes, no, primary, secondary) {
			const text = (message || "").toString();
			const is_this_doctype =
				cur_frm && cur_frm.doctype === "Idle Fixed Asset Declaration";

			if (
				is_this_doctype &&
				cur_frm.doc.scrap_type === "Fixed Asset" &&
				(
					text.includes("Send") ||
					text.includes("Approve") ||
					text.includes("Reject")
				)
			) {
				let action = "Send";
				if (text.includes("Approve")) action = "Approve";
				else if (text.includes("Reject")) action = "Reject";

				const d = new frappe.ui.Dialog({
					title: __(action),
					fields: [
						{
							fieldtype: "Small Text",
							fieldname: "remarks",
							label: __("Remarks"),
							reqd: 1
						}
					],
					primary_action_label: __(action),
					primary_action(values) {
						if (!values.remarks || !values.remarks.trim()) {
							frappe.msgprint(__("Remarks is mandatory"));
							return;
						}

						frappe.call({
							method: "scrap_management.scrap_management.doctype.idle_fixed_asset_declaration.idle_fixed_asset_declaration.update_approval_remarks",
							args: {
								docname: frm.doc.name,
								stage: frm.doc.workflow_state,
								remarks: values.remarks,
								action: action
							},
							callback() {
								d.hide();
								if (yes) yes();  // 🔥 THIS CONTINUES WORKFLOW
								frm.reload_doc();
							}
						});
					}
				});

				d.show();
				return;
			}

			return original_confirm.call(
				this,
				message,
				yes,
				no,
				primary,
				secondary
			);
		};
	}
});


frappe.ui.form.on('Idle Fixed Asset Declaration', {

    type_of_fixed_assest(frm) {

        if (!frm.doc.type_of_fixed_assest) return;

        let type = frm.doc.type_of_fixed_assest;

        // Part 1 Assets
        if ([
            "Civil structures and Furniture & Fixtures",
            "I.T assets including hardware and software",
            "Plant & Machinery including engineering and utility - instruments and equipment",
            "Vehicles"
        ].includes(type)) {

            frm.set_value(
                "particulars",
                "Part 1 : All asset other then R&d and QA/QC FA (Except part2, part3 and part4)"
            );
        }

        // Part 3
        else if (type === "QC instruments and equipment") {

            frm.set_value(
                "particulars",
                "Part 3 : QA/QC equipment and instrument and equipment FA"
            );
        }

        // Part 2
        else if (type === "R&D instruments and equipment") {

            frm.set_value(
                "particulars",
                "Part 2 : R&d equipment and instrument and equipment FA"
            );
        }

        // Part 4
        else if (type === "Others") {

            frm.set_value(
                "particulars",
                "Part 4 : All Assets except covered In part1, part2 and part3"
            );
        }
    }

});







/* ======================================================
   FILTERS
====================================================== */

function apply_cost_center_filter(frm) {
    frm.set_query('cost_center', () => {
        if (!frm.doc.company_name) return {};
        return { filters: { company_name: frm.doc.company_name } };
    });
}

function apply_particulars_filter(frm) {
    frm.set_query('particulars', () => {
        if (!frm.doc.scrap_type) return {};
        return { filters: { scrap_type: frm.doc.scrap_type } };
    });
}


// frappe.ui.form.on('Idle Fixed Asset Declaration', {

//     before_workflow_action(frm) {

//         const action = frm.selected_workflow_action;

//         if (!["Send", "Approve", "Reject"].includes(action)) {
//             return;
//         }

//         frappe.validated = false;

//         const dialog = new frappe.ui.Dialog({
//             title: `${action} Remarks`,
//             fields: [
//                 {
//                     fieldtype: "Small Text",
//                     fieldname: "remarks",
//                     label: "Remarks",
//                     reqd: 1
//                 }
//             ],
//             primary_action_label: `Confirm ${action}`,
//             primary_action(values) {

//                 if (!values.remarks) {
//                     frappe.msgprint("Remarks is mandatory");
//                     return;
//                 }

//                 // 1️⃣ Save remarks first
//                 frappe.call({
//                     method: "scrap_management.scrap_management.doctype.fixed_asset_inactive_list.fixed_asset_inactive_list.update_approval_remarks",
//                     args: {
//                         docname: frm.doc.name,
//                         remarks: values.remarks,
//                         action: action,
//                         workflow_state: frm.doc.workflow_state
//                     },
//                     callback: function(r) {

//                         if (!r.exc) {

//                             dialog.hide();

//                             // 2️⃣ Now allow default workflow to continue
//                             frappe.validated = true;

//                             frm.page.clear_primary_action();
//                             frm.save();   // IMPORTANT: let Frappe handle workflow normally
//                         }
//                     }
//                 });
//             }
//         });

//         dialog.show();
//     }
// });


frappe.ui.form.on('Asset Details', {

    upload_images: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        new frappe.ui.FileUploader({
            doctype: frm.doc.doctype,
            docname: frm.doc.name,
            multiple: true,

            on_success: function(file) {

                let images = [];

                if (row.images) {
                    try {
                        images = JSON.parse(row.images);
                    } catch (e) {
                        images = [];
                    }
                }

                images.push(file.file_url);
                row.images = JSON.stringify(images);

                frm.refresh_field("asset_details");

                setTimeout(() => {
                    render_images(frm, row);
                }, 300);
            }
        });
    },

    form_render: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        setTimeout(() => {
            render_images(frm, row);
        }, 300);
    }
});

frappe.ui.form.on('Idle Fixed Asset Declaration', {

    validate(frm) {

        (frm.doc.asset_details || []).forEach(function(row, index) {

            let images = [];

            if (row.images) {
                try {
                    images = JSON.parse(row.images);
                } catch (e) {
                    images = [];
                }
            }

            if (!images.length) {
                frappe.throw(
                    `Row ${index + 1}: Upload Images is mandatory in Asset Details`
                );
            }

        });

    }

});

function render_images(frm, row) {

    let images = [];

    if (row.images) {
        try {
            images = JSON.parse(row.images);
        } catch (e) {
            images = [];
        }
    }

    let html = "";

    images.forEach((img, index) => {
        html += `
            <div style="margin-bottom:8px;">
                <a href="${img}" target="_blank">${img}</a>
                <span 
                    style="margin-left:10px; cursor:pointer; color:red;"
                    onclick="remove_image('${row.name}', ${index})">
                    ❌ Remove
                </span>
            </div>
        `;
    });

    // 🔥 Direct DOM update (works properly inside child row)
    let field = frm.fields_dict["asset_details"]
        .grid.grid_rows_by_docname[row.name]
        .grid_form.fields_dict["image_preview"];

    if (field) {
        field.$wrapper.html(html);
    }
}



window.remove_image = function(rowname, index) {

    let row = locals["Asset Details"][rowname];

    let images = JSON.parse(row.images || "[]");

    images.splice(index, 1);

    row.images = JSON.stringify(images);

    cur_frm.refresh_field("asset_details");

    setTimeout(() => {
        render_images(cur_frm, row);
    }, 300);
}




frappe.ui.form.on('Asset Table Add Row', {

    asset_qty: function(frm, cdt, cdn) {

        // Pehle neeche wali table pura clear karo
        frm.clear_table('asset_details');

        // Upar wali table ki sab rows loop karo
        (frm.doc.table_shjf || []).forEach(function(row) {

            if (!row.asset_code || !row.asset_qty) return;

            for (let i = 0; i < row.asset_qty; i++) {

                let child = frm.add_child('asset_details');

                child.asset_code = row.asset_code;
                child.asset_description = row.asset_description;
                child.asset_qty = 1;
            }
        });

        frm.refresh_field('asset_details');
    }

});



frappe.ui.form.on('Idle Fixed Asset Declaration', {

    validate(frm) {

        let total_qty = 0;

        // Upper table total qty
        (frm.doc.table_shjf || []).forEach(function(row) {
            total_qty += flt(row.asset_qty);
        });

        // Lower table row count
        let total_rows = (frm.doc.asset_details || []).length;

        if (total_rows != total_qty) {

            frappe.throw(
                `Asset Details rows (${total_rows}) must match Asset Qty (${total_qty}). Please regenerate or correct the rows.`
            );
        }
    }

});


