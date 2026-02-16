// Copyright (c) 2026, Khan Anish and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Fixed Asset Inactive List", {
// 	refresh(frm) {

// 	},
// });
// 
frappe.ui.form.on('Fixed Asset Inactive List', {

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
    "Approval Pending from Assessment HOD": "Assessment HOD",
    "Approval Pending from QA / QC Assessment Team": "QA / QC Assessment Team",
    "Approval Pending from QA/QC HOD": "QA / QC Assessment HOD",
    "Approval Pending from CFO": "CFO",
    "Approval Pending from CEO": "CEO",
    "Approve Pending from F & A Dept.": "F & A Dept.",
    "Approve Pending from F & A HOD": "F & A HOD"
};


frappe.ui.form.on("Fixed Asset Inactive List", {
	refresh(frm) {
		if (frm.__confirm_patched) return;
		frm.__confirm_patched = true;

		const original_confirm = frappe.confirm;

		frappe.confirm = function (message, yes, no, primary, secondary) {
			const text = (message || "").toString();
			const is_this_doctype =
				cur_frm && cur_frm.doctype === "Fixed Asset Inactive List";

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
							method: "scrap_management.scrap_management.doctype.fixed_asset_inactive_list.fixed_asset_inactive_list.update_approval_remarks",
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


// frappe.ui.form.on('Fixed Asset Inactive List', {

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
