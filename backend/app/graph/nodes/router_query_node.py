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
    uploaded_files = state.uploaded_files
    latest_files = state.latest_files

    print("------ uploaded_files : ------",uploaded_files)
    print("------ latest_files : ------",latest_files)

    systemPrompt = f"""
    You are a query router for a file-analysis RAG system. 
    The previous messages summary is: {summary}.
    All files in session : {uploaded_files}
    Latest uploaded files: {latest_files}

    IMPORTANT RULE: 
        - If files are present in the session, ALWAYS assume the user 
        is asking about those files unless the query is clearly conversational 
        (greetings, thanks, general questions about your capabilities).
        Never return "direct_llm" when files are present and the query could 
        relate to file content in any way.

        - If the Router is vector_search then give the extra query and those extra query should not related to each other


    Decide one mode:

    "vector_search" — user asks to FIND or SEARCH for specific facts, keywords, 
    tech, numbers, dates, sections, named entities, or whether something appears 
    in the files.
    (e.g., "What is the bonus feature?", "Is Python mentioned?", "What is the CGPA?")

    "mongo_db_retrieve" — user asks for a broad explanation or overview of an 
    ENTIRE file OR asks a vague/general question about what to do, what is 
    needed, what is required, what features exist.
    (e.g., "Summarize resume.pdf", "What do i need to build?", "What are the requirements?")

    "direct_llm" — ONLY for purely conversational queries with zero relation 
    to uploaded files.
    (e.g., "Hello", "Hi", "Good Morning", "Thanks")

    Output ONLY a raw JSON object with NO markdown, NO explanation, NO ```json fences.

    Fields:

    mode: one of "vector_search", "mongo_db_retrieve", or "direct_llm".

    CRITICAL for target_files resolution:
    When the user refers to a file informally, resolve it to ALL matching 
    filenames from {uploaded_files} or {latest_files}.

    MULTI-FILE RULE: If the user's reference is ambiguous and could match 
    multiple files (e.g. "the assignment" when multiple assignment files exist),
    include ALL matching files in target_files — do NOT pick just one.

    Examples:
    uploaded_files: ["SDE-1_ Programming Assignment.pdf", "Credex WebDev 2026 Assignment.pdf", "resume.pdf"]

    Input: "Give me summary of the assignment"
    → ALL files with "assignment" in the name match
    → {{"mode": "mongo_db_retrieve", "target_files": ["SDE-1_ Programming Assignment.pdf", "Credex WebDev 2026 Assignment.pdf"], "extra_query": null}}

    Input: "summarize the SDE assignment"  
    → Only one file matches "SDE"
    → {{"mode": "mongo_db_retrieve", "target_files": ["SDE-1_ Programming Assignment.pdf"], "extra_query": null}}

    Input: "summarize my resume"
    → {{"mode": "mongo_db_retrieve", "target_files": ["resume.pdf"], "extra_query": null}}

    When user says "assignment file", "the assignment", "this assignment" 
    → match to ALL assignment files in: {uploaded_files} or {latest_files}
    When user says "resume", "my resume", "the resume" 
    → match to the resume file in: {uploaded_files} or {latest_files}
    Always resolve informal references to ALL matching exact filenames.

    extra_query: for "vector_search" only — return 2–3 rephrased queries that 
    expand acronyms and use alternative terminology. 
    Set null for all other modes.

    Examples:

    Input: "Is MERN mentioned?"
    → {{"mode": "vector_search", "target_files": null, "extra_query": ["MongoDB Express React Node.js", "JavaScript full-stack web development", "React Node.js backend with MongoDB"]}}

    Input: "In the assignment file is Python mentioned?"
    → {{"mode": "vector_search", "target_files": ["SDE-1_ Programming Assignment.pdf","other_file_Assigment_file.pdf","surajpate.pdf], "extra_query": ["Python programming language", "Python backend FastAPI Django", "Python web framework"]}}

    Input: "What is the bonus feature i need to add?"
    → {{"mode": "vector_search", "target_files": ["SDE-1_ Programming Assignment.pdf"], "extra_query": ["bonus points", "optional features", "extra credit functionality"]}}

    Input: "Summarize resume.pdf"
    → {{"mode": "mongo_db_retrieve", "target_files": ["SurajPatelResume (10).pdf"], "extra_query": null}}

    Input: "What do i need to build?"
    → {{"mode": "mongo_db_retrieve", "target_files": null, "extra_query": null}}

    Input: "Hi"
    → {{"mode": "direct_llm", "target_files": null, "extra_query": null}}

    Always prefer "vector_search" for targeted queries. 
    Always prefer "mongo_db_retrieve" for whole-file or broad overview questions.


CRITICAL: The words "detailed", "explain", "500 words", "in depth" describe 
HOW to answer, NOT what mode to use. Always base the mode decision on WHAT 
the user is looking for, not how long or detailed they want the answer.

If the user is asking whether something is mentioned, present, or exists 
in a file → ALWAYS "vector_search", regardless of how detailed they want 
the answer.

Input: "In this assignment file is python tech mentioned give me detailed 500 word answer"
→ {{"mode": "vector_search", "target_files": ["SDE-1_ Programming Assignment.pdf"], "extra_query": ["Python programming language", "Python backend FastAPI Django", "Python web framework"]}}

Input: "Explain in detail what technologies are mentioned in the resume"
→ {{"mode": "vector_search", "target_files": ["SurajPatelResume (10).pdf"], "extra_query": ["tech stack", "programming languages", "frameworks and tools"]}}
   
   """

    msg = [
        SystemMessage(content=systemPrompt),
        HumanMessage(content=user_query),
    ]

    try:
        response = await structuredLlm.ainvoke(msg)
        print("Router decision:", response.mode)
        print("Target files:", response.target_files)
        print("Extra queries:", response.extra_query)

        return {
            "mode": response.mode,
            "extra_query": response.extra_query or [],
            "target_files": response.target_files
        }

    except Exception as e:
        print("Router error:", e)
        return {
            "mode": "direct_llm_call",
            "extra_query": [],
            "target_files": None
        }