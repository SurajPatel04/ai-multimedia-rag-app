from langgraph.graph import StateGraph, END
from app.graph.state import State
from app.graph.nodes.title_generator_node import title_generator_node
from app.graph.nodes.router_query_node import router_query_node
from app.graph.nodes.vector_search_node import vector_search_node
from app.graph.nodes.mongo_db_retrieve_node import mongo_db_retrieve_node
from app.graph.nodes.context_builder_node import context_builder_node
from app.graph.nodes.semantic_cache_check_node import semantic_cache_check_node
from app.graph.checkpointer.mongo_checkpointer import get_checkpointer

workflow = StateGraph(State)

# Nodes
workflow.add_node("title_generator",      title_generator_node)
workflow.add_node("router_query",         router_query_node)
workflow.add_node("semantic_cache_check", semantic_cache_check_node)
workflow.add_node("vector_search",        vector_search_node)
workflow.add_node("mongo_db_retrieve",    mongo_db_retrieve_node)
workflow.add_node("context_builder_node", context_builder_node)


# Conditions

def should_generate_title(state: State):
    return "generate" if state.title == "" else "skip"

def route_after_cache(state: State):
    if state.cache_hit:
        return "end"
    return state.mode


# Edges

workflow.set_entry_point("title_generator")

workflow.add_conditional_edges(
    "title_generator",
    should_generate_title,
    {
        "generate": "router_query",
        "skip":     "router_query"
    }
)

workflow.add_edge("router_query", "semantic_cache_check")

workflow.add_conditional_edges(
    "semantic_cache_check",
    route_after_cache,
    {
        "end":               END,
        "vector_search":     "vector_search",
        "mongo_db_retrieve": "mongo_db_retrieve",
        "direct_llm":        "context_builder_node"
    }
)

workflow.add_edge("vector_search",        "context_builder_node")
workflow.add_edge("mongo_db_retrieve",    "context_builder_node")
workflow.add_edge("context_builder_node", END)

graph = workflow.compile(checkpointer=get_checkpointer())