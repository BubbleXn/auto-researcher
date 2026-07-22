"""
LangGraph research workflow — builds the StateGraph that orchestrates
Planner → Searcher → Writer (and later Critic).
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agent.clients.protocols import LLMClient, SearchClient, VectorStoreClient
from app.agent.nodes.planner import PlannerNode
from app.agent.nodes.searcher import SearcherNode
from app.agent.nodes.writer import WriterNode
from app.agent.state import ResearchState


def build_research_graph(
    *,
    llm: LLMClient,
    search: SearchClient,
    vectorstore: VectorStoreClient,
) -> StateGraph:
    """
    Build the research agent graph.

    Phase 1 (Week 1-2): Planner → Searcher → Writer (linear)
    Phase 2 (Week 3): + Critic node with conditional retry edges
    """
    planner = PlannerNode(llm=llm)
    searcher = SearcherNode(search=search)
    writer = WriterNode(llm=llm)

    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner)
    graph.add_node("searcher", searcher)
    graph.add_node("writer", writer)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "writer")
    graph.add_edge("writer", END)

    return graph.compile()
