frappe.ui.form.on('Scrap Material Declaration', {

    // ======================================================
    // ONLOAD
    // ======================================================
    onload(frm) {
        apply_actual_qty_rules(frm);
    },

    // ======================================================
    // REFRESH
    // ======================================================
    refresh(frm) {

        // ---------- Checkbox custom label ----------
        const text = `
            I confirm that applicable EHS norms have been followed and the item is
            properly cleaned as per requirement. <br> &nbsp; This form will be used only for
            non-hazardous material.
        `;

        const field = frm.fields_dict.check;
        if (field && field.$wrapper) {
            const label_area = field.$wrapper.find('.label-area');

            if (!label_area.find('.custom-check-text').length) {
                label_area.html(`
                    <span class="text-danger">*</span>
                    <span class="custom-check-text">${text}</span>
                `);
            }

            field.$wrapper.find('.checkbox label').css({
                display: 'flex',
                alignItems: 'center',
                whiteSpace: 'nowrap'
            });

            label_area.css({ whiteSpace: 'nowrap' });
        }

        // ---------- Filters ----------
        apply_cost_center_filter(frm);
        apply_particulars_filter(frm);

        // ---------- Actual Qty ----------
        setTimeout(() => apply_actual_qty_rules(frm), 300);
    },

    // ======================================================
    // FIELD EVENTS
    // ======================================================
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

    workflow_state(frm) {
        setTimeout(() => apply_actual_qty_rules(frm), 300);
    },

    // ======================================================
    // VALIDATIONS
    // ======================================================
    before_save(frm) {
        validate_actual_qty(frm);
    },

    before_submit(frm) {
        validate_actual_qty(frm);
    },

    before_workflow_action(frm) {
        validate_actual_qty(frm, true);
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

/* ======================================================
   ACTUAL QTY VISIBILITY + REQUIRED
====================================================== */

function apply_actual_qty_rules(frm) {
    if (!frm.fields_dict.table?.grid) return;

    const show_actual_qty = [
        "Receiving Pending from Scrap Incharge",
        "Received by Scrap Incharge"
    ].includes(frm.doc.workflow_state) && !frm.is_new();

    // Remark should follow Actual Qty visibility
    const show_remark = show_actual_qty;

    // Actual Qty
    frm.fields_dict.table.grid.update_docfield_property(
        'actual_qty',
        'hidden',
        !show_actual_qty
    );
    frm.fields_dict.table.grid.update_docfield_property(
        'actual_qty',
        'reqd',
        show_actual_qty
    );

    // Remark by Scrap Incharge
    frm.fields_dict.table.grid.update_docfield_property(
        'remark_by_scrap_incharge',
        'hidden',
        !show_remark
    );
    frm.fields_dict.table.grid.update_docfield_property(
        'remark_by_scrap_incharge',
        'reqd',
        false
    );

    frm.fields_dict.table.grid.refresh();
}

/* ======================================================
   REASON FOR GENERATION - 3 WORDS VALIDATION
====================================================== */

frappe.ui.form.on('Scrap Material Declaration', {
    validate(frm) {
        (frm.doc.table || []).forEach(row => {
            if (row.reason_for_generation) {
                let words = row.reason_for_generation.trim().split(/\s+/);

                if (words.length < 3) {
                    frappe.throw(
                        `Row ${row.idx}: Reason for Generation must contain at least 3 words`
                    );
                }
            }
        });
    }
});

/* ======================================================
   FIXED ASSETS UI HANDLING
====================================================== */

frappe.ui.form.on('Scrap Material Declaration', {
    refresh(frm) {
        handle_fixed_asset_ui(frm);
        update_particulars_label(frm);
    },

    scrap_type(frm) {
        handle_fixed_asset_ui(frm);
        update_particulars_label(frm);
    }
});

function handle_fixed_asset_ui(frm) {
    const is_fixed_asset = frm.doc.scrap_type === "Fixed Asset";

    // 1️⃣ Checkbox hide/show
    frm.set_df_property('check', 'hidden', is_fixed_asset);

    // 2️⃣ Scrap Details child table hide/show
    frm.set_df_property('table', 'hidden', is_fixed_asset);

    // 3️⃣ Asset Details child table show/hide
    frm.set_df_property('asset_details', 'hidden', !is_fixed_asset);

    frm.refresh_fields(['check', 'table', 'asset_details']);
}

function update_particulars_label(frm) {
    if (frm.doc.scrap_type === "Fixed Asset") {
        frm.set_df_property('particulars', 'label', 'FA Declaration Type');
    } else {
        frm.set_df_property('particulars', 'label', 'Particulars');
    }

    frm.refresh_field('particulars');
}

/* ======================================================
   ACTUAL QTY VALIDATION
====================================================== */

function validate_actual_qty(frm, is_workflow = false) {

    if (is_workflow) {
        if (frm.selected_workflow_action !== "Receive") return;
    } else {
        if (![
            "Receiving Pending from Scrap Incharge",
            "Received by Scrap Incharge"
        ].includes(frm.doc.workflow_state)) return;
    }

    const missing = (frm.doc.table || [])
        .filter(r => !r.actual_qty)
        .map(r => r.idx);

    if (missing.length) {
        frappe.throw(
            `Actual Qty is mandatory in Scrap Details (Row(s): ${missing.join(", ")})`
        );
    }
}

/* ======================================================
   FIXED ASSET APPROVAL MAP (Updated with new states)
====================================================== */

const FIXED_ASSET_APPROVAL_MAP = {
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
};

// frappe.ui.form.on('Scrap Material Declaration', {

//     // ======================================================
//     // WORKFLOW HANDLER (SINGLE SOURCE OF TRUTH)
//     // ======================================================
//     before_workflow_action(frm) {

//         // Only Fixed Asset approvals need remarks popup
//         if (frm.doc.scrap_type !== "Fixed Asset") return;

//         const action = frm.selected_workflow_action;
//         if (!["Approve", "Reject"].includes(action)) return;

//         const stage = FIXED_ASSET_APPROVAL_MAP[frm.doc.workflow_state];
//         if (!stage) return;

//         // ⛔ STOP WORKFLOW
//         frappe.validated = false;

//         const d = new frappe.ui.Dialog({
//             title: `${stage} ${action} Remarks`,
//             fields: [
//                 {
//                     fieldtype: "Small Text",
//                     fieldname: "remarks",
//                     label: "Remarks",
//                     reqd: true
//                 }
//             ],
//             primary_action_label: `Confirm ${action}`,
//             primary_action(values) {
//                 console.log(values)

//                 if (!values.remarks || !values.remarks.trim()) {
//                     frappe.msgprint("Remarks is mandatory");
//                     return;
//                 }

//                 frappe.call({
//                     method: "scrap_management.scrap_management.doctype.scrap_declaration_list.scrap_declaration_list.update_approval_remarks",
//                     args: {
//                         docname: frm.doc.name,
//                         stage: stage,
//                         remarks: values.remarks,
//                         action: action
//                     },
//                     callback() {

//                         d.hide();

//                         frappe.validated = true;
//                         frm.script_manager.trigger("apply_workflow");

//                         frm.reload_doc();
//                     }
//                 });
//             }
//         });

//         d.show();

//         d.onhide = () => {
//             frappe.validated = false;
//         };
//     }
// });



//2
// frappe.ui.form.on("Scrap Material Declaration", {
// 	refresh(frm) {
// 		if (frm.__confirm_patched) return;
// 		frm.__confirm_patched = true;

// 		const original_confirm = frappe.confirm;

// 		frappe.confirm = function (message, yes, no, primary, secondary) {
// 			const text = (message || "").toString();
// 			const is_this_doctype =
// 				cur_frm && cur_frm.doctype === "Scrap Material Declaration";

// 			// --- CUSTOM APPROVE DIALOG ---
// 			if (is_this_doctype && text.includes("Approve")) {
// 				const d = new frappe.ui.Dialog({
// 					title: __("Approve"),
// 					fields: [
// 						{
// 							fieldtype: "Small Text",
// 							fieldname: "remarks",
// 							label: __("Remarks"),
// 							reqd: 1
// 						}
// 					],
// 					primary_action_label: __("Approve"),
// 					primary_action(values) {
// 						if (!values.remarks) {
// 							frappe.msgprint(__("Remarks is mandatory"));
// 							return;
// 						}

// 						// store remarks (optional: adjust fieldname if needed)
// 						frm.set_value("workflow_remarks", values.remarks);

// 						d.hide();
// 						if (yes) yes(); // proceed with workflow
// 					}
// 				});

// 				d.show();
// 				return;
// 			}

// 			// --- AUTO CONFIRM SEND & REJECT ---
// 			if (
// 				is_this_doctype &&
// 				(text.includes("Send") || text.includes("Reject"))
// 			) {
// 				if (yes) yes();
// 				return;
// 			}

// 			// fallback to original confirm
// 			return original_confirm.call(
// 				this,
// 				message,
// 				yes,
// 				no,
// 				primary,
// 				secondary
// 			);
// 		};
// 	}
// });




frappe.ui.form.on("Scrap Material Declaration", {
	refresh(frm) {
		if (frm.__confirm_patched) return;
		frm.__confirm_patched = true;

		const original_confirm = frappe.confirm;

		frappe.confirm = function (message, yes, no, primary, secondary) {
			const text = (message || "").toString();
			const is_this_doctype =
				cur_frm && cur_frm.doctype === "Scrap Material Declaration";

			// 🔥 APPLY ONLY FOR FIXED ASSET
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
							method: "scrap_management.scrap_management.doctype.scrap_declaration_list.scrap_declaration_list.update_approval_remarks",
							args: {
								docname: frm.doc.name,
								stage: frm.doc.workflow_state,
								remarks: values.remarks,
								action: action
							},
							callback() {
								d.hide();
								if (yes) yes(); // continue workflow
								frm.reload_doc();
							}
						});
					}
				});

				d.show();
				return;
			}

			// fallback to default behaviour
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
