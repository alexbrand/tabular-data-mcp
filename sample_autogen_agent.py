import argparse
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, SseServerParams

data_analyst_system_prompt = """You are a helpful AI assistant that answers questions based on data files.

You have access to a tool that allows you to run python code in a secure sandbox. When writing python code for this tool, don't attempt to import libraries nor include any import statements in your code. The environment already has most things of interest pre-loaded. To get data or information back from the executed code, make sure to use print() to print the information you are looking for.
"""


async def main(task: str):
    tabular_mcp_server = SseServerParams(url="http://localhost:8000/sse")

    async with McpWorkbench(tabular_mcp_server) as workbench:
        model_client = OpenAIChatCompletionClient(
            #model="gpt-4o-2024-08-06",
            model="gpt-4.1-2025-04-14",
            # api_key="sk-...", # Optional if you have an OPENAI_API_KEY env variable set.
        )

        # Create the primary agent.
        primary_agent = AssistantAgent(
            "data_analyst",
            model_client=model_client,
            system_message=data_analyst_system_prompt,
            workbench=workbench,
        )

        # Create a team with the primary and critic agents.
        team = MagenticOneGroupChat(
            [primary_agent],
            model_client=model_client,
        )

        await Console(team.run_stream(task=task))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run autogen agent with a custom task")
    parser.add_argument("task", help="The task for the agent to perform")
    args = parser.parse_args()
    
    asyncio.run(main(args.task))
