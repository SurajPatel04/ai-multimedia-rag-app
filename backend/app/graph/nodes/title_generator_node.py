# app/graph/nodes/title_generator_node.py

from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.state import State
from app.utils.llm import llm
from app.models.chat_session import ChatSession

async def title_generator_node(state: State):

    print("----- TITLE GENERATOR NODE -----")

    if state.message_index > 0:
        return {}


    system_prompt = """
    Generate a short, concise title (max 6 words) for this chat session
    based on the user's first message.
    Return ONLY the title, nothing else.
    Example: "Resume Analysis for John", "Audio File Summary"
    """
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=state.query)
    ])

    title = response.content.strip()

    await ChatSession.find_one(
        ChatSession.session_id == state.session_id
    ).update({"$set": {"title": title}})

    print(f"Title generated: {title}")

    return {
        "title": title
    }