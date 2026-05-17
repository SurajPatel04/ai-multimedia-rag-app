from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.state import State
from app.utils.llm import get_google_llm
from app.graph.schemas import TitleGenerationSchema
from app.models.chat_session import ChatSession

async def title_generator_node(state: State):
    llm = get_google_llm()

    if state.message_index > 0:
        return {}

    llm_with_structure = llm.with_structured_output(TitleGenerationSchema)

    file_names = state.uploaded_files or state.latest_files or []
    file_context = (
        f"Uploaded files: {', '.join(file_names)}"
        if file_names
        else "No files uploaded"
    )

    system_prompt = f"""
    Generate a short, concise title (max 6 words) for this chat session
    based on the user's first message and the uploaded file names.

    {file_context}

    RULES:
    - If files are uploaded, include the file name or topic from the file name in the title
    - Make the title specific to the actual file, not generic
    - Max 6 words
    - Return ONLY the title, nothing else

    Examples:
    files: ["SurajPatelResume.pdf"]    → "Resume Review for Suraj Patel"
    files: ["lecture_audio.mp3"]       → "Lecture Audio Analysis"
    files: ["meeting_recording.mp4"]   → "Meeting Recording Summary"
    files: ["SDE-1_Assignment.pdf"]    → "SDE-1 Assignment Breakdown"
    no files:                          → "General Chat Session"
    """

    response = await llm_with_structure.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=state.query)
    ])

    title = response.title

    await ChatSession.find_one(
        ChatSession.session_id == state.session_id
    ).update({"$set": {"title": title}})

    print(f"Title generated: {title}")

    return {"title": title}