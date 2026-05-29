import os
import subprocess
from app.helpers.pdf_reader import process_pdf

def convert_word_to_pdf(docx_path: str, output_dir: str) -> str:
    try:
        subprocess.run([
            "libreoffice", "--headless", "--convert-to", "pdf", 
            "--outdir", output_dir, docx_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        base_name = os.path.basename(docx_path)
        pdf_name = os.path.splitext(base_name)[0] + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_name)
        
        if os.path.exists(pdf_path):
            return pdf_path
        else:
            raise Exception("LibreOffice conversion completed but PDF was not found.")
            
    except FileNotFoundError:
        raise Exception("LibreOffice is not installed. Please run: sudo apt install libreoffice")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode()}")

def process_word(file_path: str):
    """Converts Word to PDF to preserve page numbers, then processes as PDF."""
    output_dir = os.path.dirname(file_path)
    
    pdf_path = convert_word_to_pdf(file_path, output_dir)
    
    try:
        return process_pdf(pdf_path)
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
