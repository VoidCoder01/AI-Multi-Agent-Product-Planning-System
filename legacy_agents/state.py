import operator
from typing import TypedDict, Annotated, List, Optional

class AgentState(TypedDict):
    user_idea: str
    chat_history: Annotated[List[str], operator.add]
    clarification_done: bool
    project_brief: Optional[str]
    prd: Optional[str]
    epics: Optional[str]
    stories: Optional[str]
    tasks: Optional[str]
