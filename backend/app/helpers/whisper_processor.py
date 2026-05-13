from langchain_core.documents import Document
from app.helpers.text_splitter import text_splitter


def process_transcript(transcript_segments,source: str):
    splitter = text_splitter()
    processed_chunks = []
    for index, segment in enumerate( transcript_segments):
        text = segment["text"]
        start_time = segment["start"]
        end_time = segment["end"]
        chunks = splitter.create_documents(
            texts=[text],
            metadatas=[{
                "chunk_index": index,
                "chunk_method": "WhisperProcessor",
                "char_count": len(text),
                "start_time": start_time,
                "end_time": end_time,
                "source": source
            }]
        )

        processed_chunks.extend(chunks)

    return processed_chunks