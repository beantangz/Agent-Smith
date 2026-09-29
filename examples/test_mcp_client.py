import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def main() -> None:
    project_root = Path(__file__).parent.parent #path vers racine (parent.parent)

    server_path = ( # path vers fichier serveur
        project_root / "mcp_tools_mbpp.py"
    ).resolve()

    task_path = ( # path vers task
        project_root
        / "examples"
        / "mbpp_square.json"
    ).resolve()

    server_parameters = StdioServerParameters( # configuraton du serveur
        command=sys.executable, # version python du bin
        args=[str(server_path)], # chemin vers le fichier serveur mbpp_tools_mbpp.py
        env={
            "MBPP_TASK_FILE": str(task_path),
        },
    )

    async with stdio_client( # lancement du serveur en sous processus (stdio_client) avec flux
        server_parameters
    ) as (read_stream, write_stream): # flux lecture ecriture serveur
        async with ClientSession( # creation session client
            read_stream,
            write_stream, # flux lecture ecriture client (memes que serveur)
        ) as session:
            await session.initialize() # connexion serveur/client

            tools_result = await session.list_tools() # client demande tools

            print("=== AVAILABLE TOOLS ===")

            for tool in tools_result.tools: # affichage tools
                print(f"Name: {tool.name}")
                print(
                    f"Description: {tool.description}"
                )
                print(
                    f"Schema: {tool.input_schema}"
                )

            solution = """
def square(number):
    return number * number
"""

            tool_result = await session.call_tool( # appel fonction du tool, qui va creer un process enfant pour s'executer
                "run_tests",
                {
                    "solution": solution,
                },
            )

            print("\n=== TOOL RESULT ===")

            for block in tool_result.content:
                if isinstance(block, TextContent):
                    print(block.text)


if __name__ == "__main__":
    asyncio.run(main())