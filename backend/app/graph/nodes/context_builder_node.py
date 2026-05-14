from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.state import State

async def context_builder_node(state: State):

    print("----- RESPONSE GENERATION NODE -----")

    if state.mode == "direct_llm":
        system_prompt = """
            You are a helpful AI assistant.
            Answer the user's message in a friendly and conversational way.
            You can use the chat history for context.
        """
    else:
        EMPTY_CONTEXT_SIGNALS = {
            "no relevant content found for your query.",
            "no context available.",
    ""
}
        has_context = (
    bool(state.context)
    and state.context.strip().lower() not in EMPTY_CONTEXT_SIGNALS
)

        context_value = state.context if has_context else "No context available."

        system_prompt = f"""
    You are a helpful AI assistant.
    And do not mention the context in your response. Just answer the user's question.
    And multiple files context provided then explain properly each data what need to provide 

    {"Rules:" if has_context else ""}
    {"- Answer only from the given context." if has_context else ""}
    {"- If the context has timestamps (audio/video), mention them." if has_context else ""}
    {"- If the context contains multiple files, ensure your answer addresses or summarizes each file explicitly." if has_context else ""}
    {"- Be concise and clear." if has_context else ""}

    {f"Context:{chr(10)}{context_value}" if has_context else 
    "No files were uploaded. Answer the user's question conversationally based on your general knowledge. chat history"}
    """
        print(system_prompt)

    if state.mode == "direct_llm":
        user_prompt = state.query
    else:
        user_prompt = f"""
            User Question:
            {state.query}
        """

    llm_messages = [
        SystemMessage(content=system_prompt),
        *state.chat_history,
        HumanMessage(content=user_prompt),
    ]

    updated_chat_history = [
        *state.chat_history,
        HumanMessage(content=state.query),
    ]

    return {
        "messages":     llm_messages,
        "chat_history": updated_chat_history
    }