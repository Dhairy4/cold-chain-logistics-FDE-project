import sys
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent_tools import (
    fetch_corridor_conditions,
    query_telemetry_db,
    search_compliance_sop,
)

# ==========================================
# 1. SETUP & PATH RESOLUTION
# ==========================================
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parents[0]

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


load_dotenv(project_root / ".env")


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ==========================================
# 2. FACTORY INITIALIZATION: AGENT REASONER LLM
# ==========================================


llm = ChatNVIDIA(model="nvidia/nemotron-3.5-super-vl-120b-a12b")

fde_tools = [query_telemetry_db, fetch_corridor_conditions, search_compliance_sop]
llm_with_tools = llm.bind_tools(fde_tools)


# ==========================================
# 3. GRAPH ARCHITECTURE ASSEMBLY
# ==========================================
def reasoning_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


print("⚙️ Compiling LangGraph FDE Orchestrator...")
graph_builder = StateGraph(AgentState)
graph_builder.add_node("reasoner", reasoning_node)
graph_builder.add_node("tools", ToolNode(fde_tools))

graph_builder.add_edge(START, "reasoner")
graph_builder.add_conditional_edges("reasoner", tools_condition)
graph_builder.add_edge("tools", "reasoner")

fde_agent = graph_builder.compile(checkpointer=MemorySaver())

# ==========================================
# 4. CHAT LOOP TESTING PANEL
# ==========================================
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("🚀 FDE Supply Chain Orchestrator State Machine Online")
    print("=" * 55 + "\n")

    # Load the business-structured system prompt from the external file
    prompt_path = project_root / "src" / "prompts" / "system_prompt.txt"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_instructions = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {prompt_path}")
        system_instructions = "You are a helpful AI assistant."  # Basic fallback

    system_prompt = SystemMessage(content=system_instructions)

    thread_config = {"configurable": {"thread_id": "production_test_1"}}
    fde_agent.invoke({"messages": [system_prompt]}, config=thread_config)

    while True:
        user_input = input("\nDispatcher > ")
        if user_input.lower() in ["exit", "quit"]:
            break

        events = fde_agent.stream(
            {"messages": [("user", user_input)]},
            config=thread_config,
            stream_mode="updates",
        )
        for event in events:
            for node_name, node_state in event.items():
                if node_name == "tools":
                    print(
                        "[System] 🔄 Retrieving external data elements via ToolNode..."
                    )
                elif node_name == "reasoner":
                    latest_msg = node_state["messages"][-1]
                    if latest_msg.content:
                        print(f"\n🤖 FDE Agent:\n{latest_msg.content}")
