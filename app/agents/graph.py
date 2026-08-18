from langgraph.graph import END, StateGraph

from app.agents.nodes import AnswerNode, RetrieverNode
from app.agents.state import AgentState


def build_graph(retriever: RetrieverNode, answerer: AnswerNode):
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retriever.run)
    graph.add_node("answer", answerer.run)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
