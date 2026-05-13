from  langchain_community.document_loaders import PyMuPDFLoader
from app.helpers.text_splitter import text_splitter


def process_pdf(file_path: str):
    loader = PyMuPDFLoader(file_path)
    pages = loader.load()
    processed_chunks = []
    splitter = text_splitter()
    for page_num, page in enumerate(pages):
        chunks = splitter.create_documents(
            texts=[page.page_content],
            metadatas=[{
                **page.metadata,
                "page": page_num + 1,
                "total_pages": len(pages),
                "chunk_method":"PdfProcessor",
                "char_count": len(page.page_content),
                "source": file_path
            }]
        )
        processed_chunks.extend(chunks)
    return processed_chunks