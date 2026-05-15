from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import os
import shutil

FAISS_BASE_PATH = "faiss_indexes"


def get_user_index_path(user_id: str) -> str:
    return f"{FAISS_BASE_PATH}/{user_id}"


def store_vectors(user_id: str, session_id: str, chunks: list, embeddings, file_name: str):
    index_path = get_user_index_path(user_id)
    os.makedirs(index_path, exist_ok=True)

    documents = [
        Document(
            page_content=doc.page_content,
            metadata={
                **doc.metadata,
                "user_id":    user_id,
                "session_id": session_id,
                "file_name":  file_name
            }
        )
        for doc in chunks
    ]

    if os.path.exists(f"{index_path}/index.faiss"):
        store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        store.add_documents(documents)
    else:
        store = FAISS.from_documents(
            documents=documents,
            embedding=embeddings
        )

    store.save_local(index_path)
    # print(f"Stored {len(documents)} chunks for user: {user_id}, session: {session_id}")


def load_vector_store(user_id: str, embeddings):
    index_path = get_user_index_path(user_id)

    if not os.path.exists(f"{index_path}/index.faiss"):
        raise FileNotFoundError(f"Index not found for user: {user_id}")

    return FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True
    )


def vector_search(user_id: str, session_id: str, query: str, embeddings, top_k: int = 3, target_files: list = None):
    try:
        store = load_vector_store(user_id, embeddings)
    except FileNotFoundError:
        return []

    # Always filter by session
    search_filter = {"session_id": session_id}

    if target_files:
        search_filter["file_name"] = (
            target_files[0] if len(target_files) == 1
            else {"$in": target_files}
        )

    results = store.similarity_search(
        query,
        k=top_k * 10,
        filter=search_filter
    )

    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results[:top_k]
    ]


def delete_session_vectors(user_id: str, session_id: str, embeddings):
    index_path = get_user_index_path(user_id)

    try:
        store = load_vector_store(user_id, embeddings)
    except FileNotFoundError:
        print(f"No index found for user: {user_id}, nothing to delete")
        return

    remaining = [
        Document(
            page_content=doc.page_content,
            metadata=doc.metadata
        )
        for _, doc in store.docstore._dict.items()
        if doc.metadata.get("session_id") != session_id
    ]

    if remaining:
        new_store = FAISS.from_documents(remaining, embeddings)
        new_store.save_local(index_path)
    else:
        shutil.rmtree(index_path)

    # print(f"Deleted vectors for user: {user_id}, session: {session_id}")


def delete_user_vectors(user_id: str):
    index_path = get_user_index_path(user_id)
    if os.path.exists(index_path):
        shutil.rmtree(index_path)
        print(f"Deleted all vectors for user: {user_id}")