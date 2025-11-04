import os
import zipfile
import frappe
import docx
import fitz
import textract
import difflib
from frappe.model.document import Document
from frappe.utils.file_manager import save_file
from pdfminer.high_level import extract_text


class MinixDocumentFile(Document):
    def before_save(self):
        if self.upload_word_file:
            try:
                content = extract_text_from_file(self.upload_word_file)
                file_path = resolve_file_path(self.upload_word_file)
                ext = os.path.splitext(file_path)[1].lower()
                images = []

                if ext == ".docx":
                    images = extract_images_from_docx(file_path, self.name)
                elif ext == ".pdf":
                    images = extract_images_from_pdf(file_path, self.name)
                
                if not self.original_content:
                    self.original_content = content
                
                if not self.rich_text_content:
                    self.rich_text_content = content
                    
                if self.rich_text_content and self.original_content:
                    self.diff_output_html = get_diff_highlighted_html(self.original_content, self.rich_text_content)
                    
                self.attached_images = []
                for img in images:
                    self.append("attached_images", {
                        "upload_image": img["image"],
                        # "preview_image": img["image"]
                    })

                frappe.msgprint("File content loaded into the editor.")
            except Exception as e:
                frappe.throw(f" Failed to extract file content: {e}")


def resolve_file_path(file_url):
    if "/private/files/" in file_url:
        return frappe.get_site_path("private", "files", file_url.split("/private/files/")[-1])
    elif "/files/" in file_url:
        return frappe.get_site_path("public", "files", file_url.split("/files/")[-1])
    else:
        frappe.throw("Invalid file URL.")


def extract_text_from_file(file_url):
    path = resolve_file_path(file_url)

    if not os.path.exists(path):
        frappe.throw(f"File not found at: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".docx":
        return extract_docx(path)
    elif ext == ".doc":
        return extract_doc(path)
    elif ext == ".pdf":
        return extract_pdf(path)
    else:
        frappe.throw("Unsupported file format. Only .doc, .docx, and .pdf are supported.")


def extract_docx(path):
    doc = docx.Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs)


def extract_doc(path):
    try:
        text = textract.process(path)
        return text.decode("utf-8").strip()
    except ImportError:
        frappe.throw("The `textract` library is required for .doc files. Install it via: pip install textract")
    except Exception as e:
        frappe.throw(f"Error extracting text from .doc file: {e}")


def extract_pdf(path):
    try:
        text = extract_text(path)
        return text.strip() if text else "No text could be extracted from this PDF."
    except ImportError:
        frappe.throw("The `pdfminer.six` library is required. Install it using: pip install pdfminer.six")
    except Exception as e:
        frappe.throw(f"Error extracting text from PDF file: {e}")


def extract_images_from_docx(docx_path, docname):
    images = []
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx:
            for file in docx.namelist():
                if file.startswith('word/media/') and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_data = docx.read(file)
                    filename = file.split('/')[-1]
                    file_doc = save_file(filename, image_data, "Minix Document File", docname, is_private=False)
                    images.append({'image': file_doc.file_url})
    except Exception as e:
        frappe.throw(f"Error extracting images from DOCX: {e}")   
    return images

# def extract_images_from_docx(docx_path, docname):
#     from frappe.utils.file_manager import remove_file
#     images = []
#     new_file_urls = set()

#     try:
#         with zipfile.ZipFile(docx_path, 'r') as docx:
#             for file in docx.namelist():
#                 if file.startswith('word/media/') and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
#                     image_data = docx.read(file)
#                     filename = file.split('/')[-1]

#                     file_doc = save_file(
#                         filename, image_data,
#                         "Minix Document File", docname,
#                         is_private=False
#                     )
#                     new_file_urls.add(file_doc.file_url)
#                     images.append({'upload_image': file_doc.file_url})

#         doc = frappe.get_doc("Minix Document File", docname)
#         existing_file_urls = {img.upload_image for img in doc.attached_images}

#         removed_urls = existing_file_urls - new_file_urls
#         added_urls = new_file_urls - existing_file_urls

#         # Keep only images still in the DOCX
#         doc.attached_images = [
#             img for img in doc.attached_images if img.upload_image in new_file_urls
#         ]

#         # Optionally remove files from File table
#         for file_url in removed_urls:
#             try:
#                 remove_file(file_url)
#             except Exception:
#                 frappe.log_error(f"Failed to remove file: {file_url}")

#         # Add new image attachments
#         for img_url in added_urls:
#             doc.append("attached_images", {"upload_image": img_url})

#         doc.save()

#     except Exception as e:
#         frappe.throw(f"Error extracting images from DOCX: {e}")

#     return images


def extract_images_from_pdf(pdf_path, docname):
    images = []
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                filename = f"page_{i+1}_img_{img_index+1}.{image_ext}"
                file_doc = save_file(filename, image_bytes, "Minix Document File", docname, is_private=False)
                images.append({'image': file_doc.file_url})
    except Exception as e:
        frappe.throw(f"Error extracting images from PDF file: {e}")
    return images


def get_diff_highlighted_html(original, modified):
    differ = difflib.Differ()
    diff = list(differ.compare(original.split(), modified.split()))
    html_output = []
    for word in diff:
        if word.startswith('+ '):
            html_output.append(f"<span style='background-color: #d4f8d4;'>{word[2:]}</span>")
        elif word.startswith('- '):
            html_output.append(f"<span style='background-color: #fdd; text-decoration: line-through;'>{word[2:]}</span>")
        elif word.startswith('  '):
            html_output.append(word[2:])
    return ' '.join(html_output)