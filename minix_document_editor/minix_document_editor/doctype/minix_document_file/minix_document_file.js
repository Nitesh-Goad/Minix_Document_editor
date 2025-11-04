// Copyright (c) 2025, minix and contributors
// For license information, please see license.txt

frappe.ui.form.on('Minix Document File', {
    refresh(frm) {
        if (frm.doc.attached_images?.length > 0) {
            let html = `
                <label><strong>Extracted Images Preview</strong></label>
                <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">
            `;

            frm.doc.attached_images.forEach(img => {
                if (img.preview_image) {
                    html += `<img src="${img.preview_image}" width="120" height="120" style="object-fit:cover; border:1px solid #ccc; padding: 2px;" />`;
                }
            });
            // frm.doc.attached_images.forEach(img => {
            //     if (img.preview_image) {
            //         html += `
            //             <img src="${img.preview_image}"
            //                 style="width: 120px !important; height: 120px !important; object-fit: cover; border: 1px solid #ccc; padding: 2px;" />
            //         `;
            //     }
            // });

            html += `</div>`;
            frm.fields_dict.image_preview_html.$wrapper.html(html);
        } else {
            frm.fields_dict.image_preview_html.$wrapper.html("");
        }
        if (frm.doc.diff_output_html) {
            frm.fields_dict.diff_output_html.$wrapper.html(frm.doc.diff_output_html);
        }
    },  
});
