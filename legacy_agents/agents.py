import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from agents.state import AgentState
from agents.prompts import (
    CLARIFICATION_AGENT_PROMPT, 
    REQUIREMENT_AGENT_PROMPT,
    PM_AGENT_PROMPT,
    SCRUM_AGENT_PROMPT,
    TASK_AGENT_PROMPT
)
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM model from Environment
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

def get_chat_history_str(state: AgentState) -> str:
    return "\n".join(state.get("chat_history", []))

def save_to_docs(filename: str, content: str):
    os.makedirs("docs", exist_ok=True)
    with open(f"docs/{filename}", "w", encoding="utf-8") as f:
        f.write(content)

def clarification_agent(state: AgentState):
    prompt = PromptTemplate.from_template(CLARIFICATION_AGENT_PROMPT)
    chain = prompt | llm
    
    response = chain.invoke({
        "user_idea": state["user_idea"],
        "chat_history": get_chat_history_str(state)
    })
    
    content = response.content.strip()
    
    if content == "READY":
        return {"clarification_done": True, "chat_history": ["Agent: The requirements are clear. Submitting to the project team..."]}
    else:
        return {"clarification_done": False, "chat_history": [f"Agent: {content}"]}

def requirement_agent(state: AgentState):
    prompt = PromptTemplate.from_template(REQUIREMENT_AGENT_PROMPT)
    chain = prompt | llm
    
    response = chain.invoke({
        "user_idea": state["user_idea"],
        "chat_history": get_chat_history_str(state)
    })
    save_to_docs("1_project_brief.md", response.content)
    return {"project_brief": response.content}

def pm_agent(state: AgentState):
    prompt = PromptTemplate.from_template(PM_AGENT_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "project_brief": state["project_brief"]
    })
    save_to_docs("2_prd.md", response.content)
    return {"prd": response.content}

def scrum_agent(state: AgentState):
    prompt = PromptTemplate.from_template(SCRUM_AGENT_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "prd": state["prd"]
    })
    save_to_docs("3_epics_and_stories.md", response.content)
    # We use a single generation for Epics & Stories to simplify the prompt output
    return {"stories": response.content, "epics": response.content}

def task_agent(state: AgentState):
    prompt = PromptTemplate.from_template(TASK_AGENT_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "stories": state["stories"]
    })
    save_to_docs("4_tasks.md", response.content)
    return {"tasks": response.content}
