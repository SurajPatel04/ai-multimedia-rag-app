from langgraph.graph import StateGraph, END
from app.graph.state import State
from app.graph.nodes.title_generator_node import title_generator_node
from app.graph.nodes.router_query_node import router_query_node
from app.graph.nodes.vector_search_node import vector_search_node
from app.graph.nodes.mongo_db_retrieve_node import mongo_db_retrieve_node
from app.graph.nodes.response_generation_node import response_generation_node
from app.graph.checkpointer.mongo_checkpointer import get_checkpointer

workflow = StateGraph(State)

# -------------------------
# Add Nodes
# -------------------------

workflow.add_node("title_generator",     title_generator_node)
workflow.add_node("router_query",        router_query_node)
workflow.add_node("vector_search",       vector_search_node)
workflow.add_node("mongo_db_retrieve",   mongo_db_retrieve_node)
workflow.add_node("response_generation", response_generation_node)


# -------------------------
# Title check condition
# -------------------------

def should_generate_title(state: State):
    if state.title == "":
        return "title_generator"
    return "router_query"


# -------------------------
# Router Logic
# -------------------------

def route_query(state: State):
    if state.mode == "vector_search":
        return "vector_search"
    if state.mode == "mongo_db_retrieve":
        return "mongo_db_retrieve"
    if state.mode == "direct_llm":
        return "direct_llm"        # ✅ explicit — skip all search nodes
    return "direct_llm"            # ✅ fallback — anything else also skips search


# -------------------------
# Edges
# -------------------------

workflow.set_entry_point("title_generator")

workflow.add_conditional_edges(
    "title_generator",
    should_generate_title,
    {
        "title_generator": "router_query",
        "router_query":    "router_query"
    }
)

workflow.add_conditional_edges(
    "router_query",
    route_query,
    {
        "vector_search":       "vector_search",
        "mongo_db_retrieve":   "mongo_db_retrieve",
        "direct_llm":          "response_generation"  # ✅ goes straight to response
    }
)

workflow.add_edge("vector_search",       "response_generation")
workflow.add_edge("mongo_db_retrieve",   "response_generation")
workflow.add_edge("response_generation", END)

graph = workflow.compile(checkpointer=get_checkpointer())