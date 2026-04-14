from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from agents.research_agent import research_node
from agents.scout_agent import scout_node
from agents.writer_agent import writer_node
from agents.alert_agent import alert_node

workflow = StateGraph(AgentState)
workflow.add_node("research", research_node)
workflow.add_node("scout", scout_node)
workflow.add_node("writer", writer_node)
workflow.add_node("alert", alert_node)

workflow.add_edge(START, "research")
workflow.add_edge("research", "scout")
workflow.add_edge("scout", "writer")
workflow.add_edge("writer", "alert")
workflow.add_edge("alert", END)

career_pilot_graph = workflow.compile()
