import pandas as pd
import re
from app.helpers.text_splitter import text_splitter

def process_excel_csv(file_path: str):
    ext = file_path.rsplit(".", 1)[-1].lower()
    
    if ext == "csv":
        df_dict = {"Data": pd.read_csv(file_path)}
    else:
        # Excel
        df_dict = pd.read_excel(file_path, sheet_name=None)
        
    structured_rows = []
    
    for sheet_name, df in df_dict.items():
        if df.empty:
            continue
            
        for index, row in df.iterrows():
            row_details = []
            for col, val in row.items():
                if pd.notna(val) and str(val).strip() != "":
                    row_details.append(f"{col}: {val}")
                    
            if row_details:
                row_str = f"Sheet: {sheet_name} | Row: {index + 2} | " + ", ".join(row_details)
                structured_rows.append(row_str)

    processed_chunks = []
    splitter = text_splitter()
    
    if structured_rows:
        current_chunk_text = ""
        
        for row_str in structured_rows:
            # Group rows until we hit ~1000 characters to keep chunks dense
            if len(current_chunk_text) + len(row_str) > 1000 and current_chunk_text:
                clean_text = current_chunk_text.strip()
                chunks = splitter.create_documents(
                    texts=[clean_text],
                    metadatas=[{
                        "chunk_method": "ExcelCSVProcessor",
                        "char_count": len(clean_text),
                        "source": file_path
                    }]
                )
                processed_chunks.extend(chunks)
                current_chunk_text = row_str + "\n"
            else:
                current_chunk_text += row_str + "\n"
                
        # Process the last chunk
        if current_chunk_text:
            clean_text = current_chunk_text.strip()
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
