"""
LangGraph research workflow — builds the StateGraph that orchestrates
Planner → Searcher → Critic → HumanFeedback → Writer with conditional retry loops.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agent.clients.protocols import LLMClient, SearchClient, VectorStoreClient
from app.agent.nodes.critic import CriticNode
from app.agent.nodes.human_feedback import HumanFeedbackNode
from app.agent.nodes.planner import PlannerNode
from app.agent.nodes.searcher import SearcherNode
from app.agent.nodes.writer import WriterNode
from app.agent.state import ResearchPhase, ResearchState


def _route_after_critic(state: dict[str, Any]) -> str:
    """Route after the Critic node: retry search, proceed to writing, or end."""
    recommendation = state.get("critique", {}).get("recommendation")
    phase = state.get("phase", "")

    if recommendation == "proceed":
        return "human_feedback"
    elif recommendation == "retry_search" and phase == "searching":
        return "searcher"
    else:
        return END


def _route_after_feedback(state: dict[str, Any]) -> str:
    """Route after human feedback: back to searcher or proceed to writer."""
    phase = state.get("phase", "")
    if phase == ResearchPhase.SEARCHING.value:
        return "searcher"
    return "writer"


def build_research_graph(
    *,
    llm: LLMClient,
    search: SearchClient,
    vectorstore: VectorStoreClient,
    checkpointer=None,
):
    """
    Build and compile the research agent graph.

    When checkpointer is provided, interrupt() in HumanFeedbackNode will
    persist state and allow resume via Command(resume=...).
    """
    planner = PlannerNode(llm=llm)
    searcher = SearcherNode(search=search, vectorstore=vectorstore)
    critic = CriticNode(llm=llm)
    human_feedback = HumanFeedbackNode()
    writer = WriterNode(llm=llm, vectorstore=vectorstore)

    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner)
    graph.add_node("searcher", searcher)
    graph.add_node("critic", critic)
    graph.add_node("human_feedback", human_feedback)
    graph.add_node("writer", writer)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "critic")
    graph.add_conditional_edges("critic", _route_after_critic)
    graph.add_conditional_edges("human_feedback", _route_after_feedback)
    graph.add_edge("writer", END)

    return graph.compile(checkpointer=checkpointer)
