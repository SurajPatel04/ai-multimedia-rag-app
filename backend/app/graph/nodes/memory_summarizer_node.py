# memory_summarizer_node.py
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm import llm
from app.graph.workflow import graph

async def run_summarizer_background(state: dict, config: dict):

    print("----- BACKGROUND SUMMARIZER RUNNING -----")

    chat_history          = state.get("chat_history", [])
    messages_to_summarize = chat_history[:3]
    remaining_messages    = chat_history[3:]

    conversation_text = ""
    for msg in messages_to_summarize:
        role = "User" if isinstance(msg, HumanMessage) else "AI"
        conversation_text += f"{role}: {msg.content}\n\n"

    response = await llm.ainvoke([
        SystemMessage(content="Summarize this conversation concisely. Preserve key facts."),
        HumanMessage(content=f"""
Previous summary:
{state.get("summary", "")}

Conversation:
{conversation_text}
""")
    ])

    # ✅ Save directly to graph state
    await graph.aupdate_state(
        config,
        {
            "summary": response.content,
            "chat_history": remaining_messages
        }
    )

    print("✅ Background summarizer done — summary saved directly to checkpoint")