from app.graph import state
from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.state import State

async def context_builder_node(state: State):

    print("----- CONTEXT BUILDER NODE -----")

    summary_section = (
        f"\n\nSummary of earlier conversation:\n{state.summary}"
        if state.summary
        else ""
    )

    if state.mode == "direct_llm":
        system_prompt = f"""
            You are a helpful AI assistant.
            Answer the user's message in a friendly and conversational way.
            You can use the chat history for context.

            Build By Suraj Patel  And you can connect surajpatel9390@gmail.com for more information.
            Your capabilities include:
            - Answering questions
            - Understanding PDFs, audio, videos, and documents
            - Summarizing conversations and files
            - Helping with coding, research, writing, and analysis
            - Maintaining contextual memory across sessions

            You should:
            - Be concise but helpful
            - Speak naturally and professionally
            - Avoid mentioning internal model providers unless explicitly asked
            - Focus on helping the user accomplish tasks efficiently
            
            {summary_section}
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
        You are an intelligent AI assistant inside a multimedia conversational platform.
        And Build By Suraj Patel  And you can connect surajpatel9390@gmail.com for more information.
        Do not mention "the context" in your response. Just answer the user's question directly.


        Your capabilities include:
        - Answering questions
        - Understanding PDFs, audio, videos, and documents
        - Summarizing conversations and files
        - Helping with coding, research, writing, and analysis
        - Maintaining contextual memory across sessions

        You should:
        - Be concise but helpful
        - Speak naturally and professionally
        - Avoid mentioning internal model providers unless explicitly asked
        - Focus on helping the user accomplish tasks efficiently

        If multiple files are provided, address each one explicitly.
        {summary_section}

        {"Rules:" if has_context else ""}
        {"- Answer only from the given context." if has_context else ""}
        {"- Read the context carefully before answering. If the user asks for a 'heading', ensure you are referencing the actual page where the heading exists, not a page where it is just mentioned in a list." if has_context else ""}
        {"- CRITICAL: When using information from the context, you MUST cite the source using the EXACT bracket format provided in the context blocks, and include a short exact quote from the text for highlighting." if has_context else ""}
        {"  Examples of correct citation formats:" if has_context else ""}
        {"    * For PDFs/Word/Excel: [document.pdf | Page 2 | \"exact short quote from text\"]" if has_context else ""}
        {"    * For Audio/Video: [media.mp4 | 02:15 - 02:45]" if has_context else ""}
        {"  Do not alter the brackets or the spacing." if has_context else ""}
        {"- If the context contains multiple files, ensure your answer addresses or summarizes each file explicitly." if has_context else ""}
        {"- When the context is from a CSV or Excel file, or when presenting tabular data, ALWAYS format your response using a clean Markdown table. if needed" if has_context else ""}
        {"- If the user asks for a comparison, ALWAYS present the comparison in a Markdown table." if has_context else ""}
        {"- Be concise and clear." if has_context else ""}

        {f"Context:\n{context_value}" if has_context else
        "No files were uploaded. Answer the user's question conversationally based on your general knowledge and chat history."}
        """

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

    # print("LLM Message ----------------", llm_messages)

    updated_chat_history = [
        *state.chat_history,
        HumanMessage(content=state.query),
    ]

    return {
        "messages":     llm_messages,
        "chat_history": updated_chat_history
    }