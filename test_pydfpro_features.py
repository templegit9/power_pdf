import os
import shutil
import tempfile
from pydfpro import (
    handle_merge, handle_split, handle_reorder, handle_delete, handle_rotate,
    handle_extract_text, handle_extract_images, handle_pdf_to_image, handle_images_to_pdf,
    handle_add_watermark, handle_add_page_numbers, handle_encrypt, handle_decrypt, handle_compress
)
from PyPDF2 import PdfReader
from PIL import Image, ImageDraw

def create_sample_pdf(path, num_pages=3, text_prefix="Page"):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    c = canvas.Canvas(path, pagesize=letter)
    for i in range(num_pages):
        c.drawString(100, 750, f"{text_prefix} {i+1}")
        c.showPage()
    c.save()

def create_sample_image(path, color, size=(200, 200)):
    img = Image.new("RGB", size, color)
    d = ImageDraw.Draw(img)
    d.text((10, 10), color, fill=(255,255,255))
    img.save(path)

def file_exists(path):
    return os.path.exists(path) and os.path.getsize(path) > 0

def test_merge(tempdir):
    pdf1 = os.path.join(tempdir, "merge1.pdf")
    pdf2 = os.path.join(tempdir, "merge2.pdf")
    out = os.path.join(tempdir, "merged.pdf")
    create_sample_pdf(pdf1, 2, "A")
    create_sample_pdf(pdf2, 3, "B")
    class Args: pass
    Args.input_files = [pdf1, pdf2]
    Args.output_file = out
    handle_merge(Args)
    return file_exists(out) and len(PdfReader(out).pages) == 5

def test_split(tempdir):
    pdf = os.path.join(tempdir, "split.pdf")
    create_sample_pdf(pdf, 4)
    out_dir = os.path.join(tempdir, "split_out")
    os.makedirs(out_dir)
    class Args: pass
    Args.input_file = pdf
    Args.output_path = out_dir
    Args.ranges = "1-2,3-4"
    Args.every_n_pages = None
    Args.each_page = False
    handle_split(Args)
    files = [f for f in os.listdir(out_dir) if f.endswith('.pdf')]
    return len(files) == 2

def test_reorder(tempdir):
    pdf = os.path.join(tempdir, "reorder.pdf")
    out = os.path.join(tempdir, "reordered.pdf")
    create_sample_pdf(pdf, 3)
    class Args: pass
    Args.input_file = pdf
    Args.page_order = "3,2,1"
    Args.output_file = out
    handle_reorder(Args)
    return file_exists(out) and len(PdfReader(out).pages) == 3

def test_delete(tempdir):
    pdf = os.path.join(tempdir, "delete.pdf")
    out = os.path.join(tempdir, "deleted.pdf")
    create_sample_pdf(pdf, 4)
    class Args: pass
    Args.input_file = pdf
    Args.pages_to_delete = "2,4"
    Args.output_file = out
    handle_delete(Args)
    return file_exists(out) and len(PdfReader(out).pages) == 2

def test_rotate(tempdir):
    pdf = os.path.join(tempdir, "rotate.pdf")
    out = os.path.join(tempdir, "rotated.pdf")
    create_sample_pdf(pdf, 2)
    class Args: pass
    Args.input_file = pdf
    Args.pages = "1"
    Args.angle = 90
    Args.output_file = out
    handle_rotate(Args)
    return file_exists(out)

def test_extract_text(tempdir):
    pdf = os.path.join(tempdir, "extract_text.pdf")
    out = os.path.join(tempdir, "extracted.txt")
    create_sample_pdf(pdf, 1, "ExtractMe")
    class Args: pass
    Args.input_file = pdf
    Args.output_file = out
    handle_extract_text(Args)
    return file_exists(out) and "ExtractMe" in open(out, encoding="utf-8").read()

def test_extract_images(tempdir):
    pdf = os.path.join(tempdir, "extract_images.pdf")
    out_dir = os.path.join(tempdir, "img_out")
    os.makedirs(out_dir)
    # Create a PDF with an image
    img_path = os.path.join(tempdir, "img.png")
    create_sample_image(img_path, "red")
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    c = canvas.Canvas(pdf, pagesize=letter)
    c.drawImage(img_path, 100, 600, width=50, height=50)
    c.showPage()
    c.save()
    class Args: pass
    Args.input_file = pdf
    Args.output_dir = out_dir
    Args.image_format = "png"
    handle_extract_images(Args)
    files = [f for f in os.listdir(out_dir) if f.lower().endswith((".png",".jpg",".jpeg"))]
    return len(files) >= 1

def test_pdf_to_image(tempdir):
    pdf = os.path.join(tempdir, "pdf2img.pdf")
    out_dir = os.path.join(tempdir, "pdf2img_out")
    os.makedirs(out_dir)
    create_sample_pdf(pdf, 2)
    class Args: pass
    Args.input_file = pdf
    Args.output_dir_or_pattern = out_dir
    Args.pages = None
    Args.format = "png"
    Args.dpi = 100
    handle_pdf_to_image(Args)
    files = [f for f in os.listdir(out_dir) if f.lower().endswith('.png')]
    return len(files) == 2

def test_images_to_pdf(tempdir):
    img1 = os.path.join(tempdir, "img1.png")
    img2 = os.path.join(tempdir, "img2.png")
    out = os.path.join(tempdir, "imgs2pdf.pdf")
    create_sample_image(img1, "blue")
    create_sample_image(img2, "green")
    class Args: pass
    Args.input_files = [img1, img2]
    Args.output_file = out
    Args.images_per_page = None
    handle_images_to_pdf(Args)
    return file_exists(out) and len(PdfReader(out).pages) == 2

def test_add_watermark(tempdir):
    pdf = os.path.join(tempdir, "wm.pdf")
    out = os.path.join(tempdir, "wm_out.pdf")
    create_sample_pdf(pdf, 1)
    class Args: pass
    Args.input_file = pdf
    Args.output_file = out
    Args.pages = None
    Args.watermark_type = "text"
    Args.text = "WATERMARK"
    Args.font_name = "helv"
    Args.font_size = 20
    Args.font_color = "#000000"
    Args.opacity = 0.5
    Args.rotate = 0
    Args.position = "center"
    Args.image = None
    handle_add_watermark(Args)
    return file_exists(out)

def test_add_page_numbers(tempdir):
    pdf = os.path.join(tempdir, "pn.pdf")
    out = os.path.join(tempdir, "pn_out.pdf")
    create_sample_pdf(pdf, 3)
    class Args: pass
    Args.input_file = pdf
    Args.output_file = out
    Args.pages = None
    Args.position = "footer_right"
    Args.start_number = 1
    Args.font_name = "helv"
    Args.font_size = 12
    Args.font_color = "#000000"
    Args.format_string = "{page_num}"
    handle_add_page_numbers(Args)
    return file_exists(out)

def test_encrypt_decrypt(tempdir):
    pdf = os.path.join(tempdir, "enc.pdf")
    enc = os.path.join(tempdir, "enc_out.pdf")
    dec = os.path.join(tempdir, "dec_out.pdf")
    create_sample_pdf(pdf, 1)
    class Args: pass
    Args.input_file = pdf
    Args.output_file = enc
    Args.owner_password = "owner"
    Args.user_password = "user"
    Args.allow_print = True
    Args.allow_copy = True
    Args.allow_modify = True
    Args.encryption_strength = 128
    handle_encrypt(Args)
    # Now decrypt
    class DArgs: pass
    DArgs.input_file = enc
    DArgs.output_file = dec
    DArgs.password = "user"
    handle_decrypt(DArgs)
    return file_exists(enc) and file_exists(dec)

def test_compress(tempdir):
    pdf = os.path.join(tempdir, "compress.pdf")
    out = os.path.join(tempdir, "compress_out.pdf")
    create_sample_pdf(pdf, 2)
    class Args: pass
    Args.input_file = pdf
    Args.output_file = out
    Args.level = "basic"
    handle_compress(Args)
    return file_exists(out)

def main():
    tempdir = tempfile.mkdtemp(prefix="pydfpro_test_")
    results = {}
    try:
        results["merge"] = test_merge(tempdir)
        results["split"] = test_split(tempdir)
        results["reorder"] = test_reorder(tempdir)
        results["delete"] = test_delete(tempdir)
        results["rotate"] = test_rotate(tempdir)
        results["extract_text"] = test_extract_text(tempdir)
        results["extract_images"] = test_extract_images(tempdir)
        results["pdf_to_image"] = test_pdf_to_image(tempdir)
        results["images_to_pdf"] = test_images_to_pdf(tempdir)
        results["add_watermark"] = test_add_watermark(tempdir)
        results["add_page_numbers"] = test_add_page_numbers(tempdir)
        results["encrypt_decrypt"] = test_encrypt_decrypt(tempdir)
        results["compress"] = test_compress(tempdir)
    finally:
        shutil.rmtree(tempdir)
    print("\nPyDF Pro Feature Test Results:")
    for feat, passed in results.items():
        print(f"{feat:20}: {'PASS' if passed else 'FAIL'}")
    if all(results.values()):
        print("\nAll features passed basic automated tests.")
    else:
        print("\nSome features failed. See above for details.")

if __name__ == "__main__":
    main() 