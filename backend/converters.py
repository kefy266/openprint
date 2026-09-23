import os
from PIL import Image, ImageOps, ImageEnhance
from pypdf import PdfReader

SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}

def process_file_for_print(input_path: str, upload_dir: str, job_uuid: str, orientation: str = 'portrait') -> str:
    """Process any uploaded file into a high quality printable PDF file."""
    ext = os.path.splitext(input_path)[1].lower()

    if ext in SUPPORTED_IMAGE_EXTS:
        pdf_filename = f"{job_uuid}_printable.pdf"
        pdf_path = os.path.join(upload_dir, pdf_filename)
        
        with Image.open(input_path) as img:
            # Auto-orient based on EXIF camera data
            img = ImageOps.exif_transpose(img)
            
            # Convert RGBA/palette to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Auto-enhance contrast slightly for sharp text
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.2)

            w, h = img.size
            if orientation == 'auto':
                orientation = 'landscape' if w > h else 'portrait'

            # Save as 300 DPI high resolution PDF
            img.save(pdf_path, 'PDF', resolution=300.0, quality=95)

        return pdf_path

    # If already PDF or plain text
    return input_path
