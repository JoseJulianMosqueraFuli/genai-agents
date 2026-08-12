from langgraph.graph import END, StateGraph

from app.agents.nodes import AnswerNode, RetrieverNode, Router
from app.agents.state import AgentState


def build_graph(retriever: RetrieverNode, answerer: AnswerNode, router: Router):
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retriever.run)
    graph.add_node("answer", answerer.run)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
