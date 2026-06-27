from langgraph.graph import StateGraph, START, END
from app.agent.state import ReviewState
from app.agent.nodes.fetch_diff import fetch_pr_diff
from app.agent.nodes.parse_files import parse_changed_files
from app.agent.nodes.analyze_rag import analyze_with_rag
from app.agent.nodes.format_comments import format_comments
from app.agent.nodes.post_comments import post_comments
from app.agent.nodes.generate_summary import generate_summary


def build_review_graph() -> StateGraph:
    graph = StateGraph(ReviewState)

    graph.add_node("fetch_diff", fetch_pr_diff)
    graph.add_node("parse_files", parse_changed_files)
    graph.add_node("analyze_llm", analyze_with_rag)
    graph.add_node("format_comments", format_comments)
    graph.add_node("post_comments", post_comments)
    graph.add_node("generate_summary", generate_summary)

    graph.add_edge(START, "fetch_diff")
    graph.add_edge("fetch_diff", "parse_files")
    graph.add_edge("parse_files", "analyze_llm")
    graph.add_edge("analyze_llm", "format_comments")
    graph.add_edge("format_comments", "post_comments")
    graph.add_edge("post_comments", "generate_summary")
    graph.add_edge("generate_summary", END)

    return graph.compile()


review_graph = build_review_graph()
__all__ = ["review_graph", "build_review_graph"]
