from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.state import State
from app.utils.llm import llm
from app.graph.schemas import TitleGenerationSchema
from app.models.chat_session import ChatSession

async def title_generator_node(state: State):

    # print("----- TITLE GENERATOR NODE -----")

    if state.message_index > 0:
        return {}

    llm_with_structure = llm.with_structured_output(TitleGenerationSchema)
    system_prompt = """
    Generate a short, concise title (max 6 words) for this chat session
    based on the user's first message.
    Return ONLY the title, nothing else.
    Example: "Resume Analysis for John", "Audio File Summary"
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

    return {
        "title": title
    }