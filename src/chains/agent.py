import os

from src.chains.command_chains import examiner_chain
from src.utils.tools import get_current_inventory
from langchain import hub
from langchain.agents import AgentExecutor, Tool, create_openai_functions_agent
from langchain_openai import ChatOpenAI


AGENT_MODEL = os.getenv("ANTHROPIC_AGENT_MODEL")
hospital_agent_prompt = hub.pull("hwchase17/openai-functions-agent")

tools = [
    Tool(
        name="Examiner",
        func=examiner_chain.invoke,
        description="""You need to act as the orchestrator of the actions of the player in a detective game.
        You should use this tool when you need to answer questions
        about description of an object, a person, a room, its exits,
       or even feelings of an NPC.
        """,
    ),
    Tool(
        name="Inventory",
        func=get_current_inventory,
        description="""Use when asked about current player inventory, what is the player carrying.
        """,
    ),
]

chat_model = ChatOpenAI(
    model=AGENT_MODEL,
    temperature=0,
)

hospital_rag_agent = create_openai_functions_agent(
    llm=chat_model,
    prompt=hospital_agent_prompt,
    tools=tools,
)

hospital_rag_agent_executor = AgentExecutor(
    agent=hospital_rag_agent,
    tools=tools,
    return_intermediate_steps=True,
    verbose=True,
)
