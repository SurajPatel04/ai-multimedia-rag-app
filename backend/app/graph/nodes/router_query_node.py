from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import State
from app.graph.schemas import QueryRouterState
from app.utils.llm import get_google_llm

from app.utils.router_history import build_router_history



async def router_query_node(state: State):
    llm = get_google_llm()

    # print("----- QUERY ROUTER NODE -----")
    # print("Query:", state.query)
    # print("Session ID:", state.session_id)

    structuredLlm = llm.with_structured_output(QueryRouterState)

    user_query = state.query
    summary = state.summary
    uploaded_files = state.uploaded_files
    latest_files = state.latest_files

    recent_chat = build_router_history(state.chat_history)

    last_active_files = state.last_active_files

    # print("------ uploaded_files : ------",uploaded_files)
    # print("------ latest_files : ------",latest_files)

    # print("----summary: -------", state.summary)

    systemPrompt = f"""
You are a query router for a file-analysis RAG system. 
Recent conversation:
{recent_chat}

Last active files:
{last_active_files}  Means this file is used to give the answer of the last question

All files in session: {uploaded_files}
Latest uploaded files: {latest_files}

PURPOSE
Decide which service to use:
- "vector_search": for targeted queries (find specific facts, keywords, tech, numbers, dates, sections, entities, or whether something exists in the files).
- "mongo_db_retrieve": for broad, whole‑file or general questions (summarize, overview, what to do/build/need, requirements, features).
- "direct_llm": only for purely conversational messages with zero relation to files (e.g., "Hi", "Thanks", "Can you help me?").

And  - should_cache: whether the final answer should be stored in semantic cache

CACHE RULES:
    SEMANTIC CACHE POLICY

    CACHE ONLY:
    - stable educational knowledge
    - semantic retrieval answers
    - explanations about uploaded files
    - technical explanations
    - summaries that are unlikely to change

    DO NOT CACHE:
    - conversational reference questions
    - session‑dependent questions
    - repeat/regenerate requests
    - temporary conversational context
    - greetings
    - real‑time questions

RULES

1. With files present
   - ALWAYS assume the user is asking about files unless the query is clearly conversational.
   - Never return "direct_llm" when files exist and the query could relate to content in any way.

2. Informal file references
   - Resolve informal references (e.g., "this file", "the assignment", "my resume") to ALL matching filenames from {uploaded_files} or {latest_files}.
   - If the reference is ambiguous and matches multiple files, include ALL matching files in target_files (MULTI‑FILE RULE).

3. "What inside the file?"‑style phrases
   - If the user says "what inside the file?" or similar:
     - If latest_files is non‑empty, use the latest file(s) that also appear in uploaded_files.
     - If latest_files is empty, use the last file in uploaded_files.

4. Mode choice
   - Prefer "vector_search" for:
     - Is/Tell me whether X is mentioned/present?
     - What is X? (where X is a specific fact, term, number, etc.)
     - Short keyword‑based searches.
   - Prefer "mongo_db_retrieve" for:
     - "Summarize X", "Explain the whole file", "What should I build?", "What are the requirements?".
   - Use "direct_llm" only when the query is clearly conversational and unrelated to files.

5. extra_query
   - If the user asks where a specific entity, keyword, or concept is mentioned (e.g., "where is google mentioned?", "when is google mentioned in the audio", "find mentions of X"), set extra_query to ONLY contain the exact keywords or entities they are looking for (e.g., ["google", "Google"]). DO NOT generate full-sentence queries like "when is google mentioned".
   - If the user explicitly asks for an "exact word", "exact phrase", or mentions they want an exact match, set extra_query to ONLY the exact text they want to match.
   - Otherwise, for "vector_search", extra_query must be 2–3 rephrased queries that expand acronyms and use alternative terminology.
   - For "mongo_db_retrieve" and "direct_llm", set extra_query to null.

6. Formatting
   - Output ONLY a raw JSON object, with:
     {{
       "mode": one of "vector_search", "mongo_db_retrieve", "direct_llm",
       "target_files": [list of filenames] or null,
       "extra_query": [2–3 strings] or null
        - "should_cache": boolean (True if the final answer should be cached, False otherwise)
     }}
   - No markdown, no explanation, no ```json fences.

7. If the user is asking whether something is mentioned, present, or exists in a file → ALWAYS use "vector_search".

"""

    msg = [
        SystemMessage(content=systemPrompt),
        HumanMessage(content=user_query),
    ]

    try:
        response = await structuredLlm.ainvoke(msg)
        print("Respnse:  ", response)
        print("Router decision:", response.mode)
        print("Target files:", response.target_files)
        print("Extra queries:", response.extra_query)
        print("Last active files:", response.target_files if response.target_files else state.last_active_files)

        return {
            "mode": response.mode,
            "extra_query": response.extra_query or [],
            "target_files": response.target_files,
            "should_cache": response.should_cache,
            "last_active_files": (
                response.target_files
                if response.target_files
                else state.last_active_files
            )
        }

    except Exception as e:
        print("Router error:", e)
        return {
            "mode": "direct_llm",
            "extra_query": [],
            "target_files": None,
            "should_cache": False,
            "last_active_files": state.last_active_files
        }