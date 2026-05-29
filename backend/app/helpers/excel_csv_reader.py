import pandas as pd
import re
from app.helpers.text_splitter import text_splitter

def process_excel_csv(file_path: str):
    ext = file_path.rsplit(".", 1)[-1].lower()
    
    if ext == "csv":
        df = pd.read_csv(file_path)
        text = df.to_csv(index=False)
    else:
        # Excel
        df_dict = pd.read_excel(file_path, sheet_name=None)
        text_parts = []
        for sheet_name, df in df_dict.items():
            text_parts.append(f"--- Sheet: {sheet_name} ---")
            text_parts.append(df.to_csv(index=False))
        text = "\n\n".join(text_parts)

    # Clean up excessive newlines
    clean_text = re.sub(r'\n{3,}', '\n\n', text).strip()

    processed_chunks = []
    splitter = text_splitter()
    
    if clean_text:
        chunks = splitter.create_documents(
            texts=[clean_text],
            metadatas=[{
                "chunk_method": "ExcelCSVProcessor",
                "char_count": len(clean_text),
                "source": file_path
            }]
        )
        processed_chunks.extend(chunks)
    return processed_chunks
