from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from agents.agents import clarification_agent, requirement_agent, pm_agent, scrum_agent, task_agent

def route_next(state: AgentState) -> str:
    # 1. Ask for Clarification if not marked done
    if not state.get("clarification_done", False):
        return "clarification"
    
    # 2. If Clarification is complete, start the sequential pipeline
    if not state.get("project_brief"):
        return "requirement"
        
    # Done with everything
    return END

workflow = StateGraph(AgentState)

# Add all agents as discrete nodes
workflow.add_node("clarification", clarification_agent)
workflow.add_node("requirement", requirement_agent)
workflow.add_node("pm", pm_agent)
workflow.add_node("scrum", scrum_agent)
workflow.add_node("task", task_agent)

# Entrypoint: Determine what to run based on current state
workflow.add_conditional_edges(START, route_next, {
    "clarification": "clarification",
    "requirement": "requirement",
    END: END
})

# Workflow paths
workflow.add_edge("clarification", END)       # Pause Graph & wait for User Reply
workflow.add_edge("requirement", "pm")        # Requirements output feed PM
workflow.add_edge("pm", "scrum")              # PM output feed Scrum Target
workflow.add_edge("scrum", "task")            # Scrum epics/stories feed Task breakdown
workflow.add_edge("task", END)                # Output is complete!

# Expose the runnable app
app = workflow.compile()
