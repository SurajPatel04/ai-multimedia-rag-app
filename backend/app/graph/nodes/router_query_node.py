from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import State
from app.graph.schemas import QueryRouterState
from app.utils.llm import llm

async def router_query_node(state: State):

    print("----- QUERY ROUTER NODE -----")
    print("Query:", state.query)
    print("Session ID:", state.session_id)

    structuredLlm = llm.with_structured_output(QueryRouterState)

    user_query = state.query
    summary = state.summary

    systemPrompt = f"""
You are a query router for a file-analysis RAG system. 
The previous messages summery is: {summary}.

Decide one mode:

"vector_search" — user asks to FIND or SEARCH for specific facts, keywords, numbers, dates, sections, named entities, or whether something appears in the files (e.g., "What is the candidate's CGPA?", "Is MERN mentioned?", "What does section 3 say?").

"mongo_db_retrieve" — user asks for a broad explanation or overview of an ENTIRE file (e.g., "Summarize resume.pdf", "Explain this PDF", "Give an overview of the audio", "What in this", "What i need to build" these type of question).

"direct_llm" — conversational queries or those that need no file context (e.g., "Hello", "What can you do?", "Thanks").

Output a JSON object with three fields:

mode: one of "vector_search", "mongo_db_retrieve", or "direct_llm".

mongo_db_target_files: null or an array of filenames (only for "mongo_db_retrieve"; set to null when user requests all files or doesn’t name a file).
In the mongo_db call time do not give me extra query.

extra_query: for "vector_search" only — return 2–3 rephrased queries that expand acronyms and use alternative terminology/keywords (not trivial rephrasings). If mode ≠ "vector_search", set extra_query to null.

Examples (for router reference only):

Input: "Is MERN mentioned?" → mode: "vector_search", extra_query: ["MongoDB Express React Node.js", "JavaScript full‑stack web development", "React Node.js backend with MongoDB"].

Input: "Summarize resume.pdf" → mode: "mongo_db_retrieve", mongo_db_target_files: ["resume.pdf"], extra_query: null.

Input: "Hi, what can you do?" → mode: "direct_llm", mongo_db_target_files: null, extra_query: null.

Always choose the mode that best matches the user's explicit intent; prefer "vector_search" for targeted search queries and "mongo_db_retrieve" for whole‑file summaries. If ambiguous, prefer "vector_search" and include clarifying phrasing in extra_query.
"""

    msg = [
        SystemMessage(content=systemPrompt),
        HumanMessage(content=user_query),
    ]

    try:
        response = await structuredLlm.ainvoke(msg)
        print("Router decision:", response.mode)
        print("Target files:", response.mongo_db_target_files)
        print("Extra queries:", response.extra_query)

        return {
            "mode": response.mode,
            "extra_query": response.extra_query or [],
            "target_files": response.mongo_db_target_files  # ✅ was missing before
        }

    except Exception as e:
        print("Router error:", e)
        return {
            "mode": "direct_llm_call",  # safe fallback
            "extra_query": [],
            "target_files": None
        }