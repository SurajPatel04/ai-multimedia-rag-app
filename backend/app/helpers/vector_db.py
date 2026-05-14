from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import os
import shutil

FAISS_INDEX_PATH = "faiss_indexes/global"


def store_vectors(session_id: str, chunks: list, embeddings):
    """Add chunks to global FAISS index with session_id in metadata"""

    # tag every chunk with session_id
    documents = [
        Document(
            page_content=doc.page_content,
            metadata={
                **doc.metadata,
                "session_id": session_id   # ← tag with session
            }
        )
        for doc in chunks
    ]

    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

    # if global index exists → merge, else create new
    if os.path.exists(f"{FAISS_INDEX_PATH}/index.faiss"):
        store = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        store.add_documents(documents)     # ← merge into existing
    else:
        store = FAISS.from_documents(
            documents=documents,
            embedding=embeddings
        )

    store.save_local(FAISS_INDEX_PATH)
    print(f"Stored {len(documents)} chunks for session: {session_id}")


def load_vector_store(embeddings):
    """Load global FAISS index"""

    if not os.path.exists(f"{FAISS_INDEX_PATH}/index.faiss"):
        raise FileNotFoundError("Global index not found")

    return FAISS.load_local(
        FAISS_INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )


def vector_search(session_id: str, query: str, embeddings, top_k: int = 3):
    """Search only within session's chunks"""

    try:
        store = load_vector_store(embeddings)
    except FileNotFoundError:
        return []

    # search more results then filter by session_id
    results = store.similarity_search(
        query,
        k=top_k * 10,   # fetch more to filter from
        filter={"session_id": session_id}   # ← filter by session
    )

    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results[:top_k]
    ]


def delete_session_vectors(session_id: str, embeddings):
    """
    FAISS doesn't support deletion natively.
    Rebuild index without the deleted session's chunks.
    """
    try:
        store = load_vector_store(embeddings)
    except FileNotFoundError:
        print(f"No global index found, nothing to delete for session: {session_id}")
        return

    # get all docs except deleted session
    remaining_docs = [
        Document(
            page_content=doc.page_content,
            metadata=doc.metadata
        )
        for doc_id, doc in store.docstore._dict.items()
        if doc.metadata.get("session_id") != session_id
    ]

    if remaining_docs:
        new_store = FAISS.from_documents(remaining_docs, embeddings)
        new_store.save_local(FAISS_INDEX_PATH)
    else:
        # no docs left → delete entire index
        shutil.rmtree(FAISS_INDEX_PATH)

    print(f"Deleted vectors for session: {session_id}")