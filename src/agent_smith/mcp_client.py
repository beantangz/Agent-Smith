import json
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent, Tool


class MCPClientError(Exception):
    """Raised when an MCP client operation fails."""


class StdioMCPClient:
    """Persistent client connected to an MCP stdio server."""

    def __init__(
        self,
        command: str,
        args: list[str],
        env: Optional[dict[str, str]] = None,
    ) -> None:
        self.server_parameters = StdioServerParameters(
            command=command, # chemin vers executable python du env
            args=args,  # fichier a executer (ici mcp_tools_mbpp.py)
            env=env, # variables d'env, comme la task pr exemple
        )

        self._exit_stack: Optional[
            AsyncExitStack
        ] = None

        self._session: Optional[
            ClientSession
        ] = None

    async def connect(self) -> None:
        """Launch the server and initialize the MCP session."""

        if self._session is not None:
            return

        exit_stack = AsyncExitStack()

        try:
            read_stream, write_stream = ( # lancement serveur
                await exit_stack.enter_async_context(
                    stdio_client(
                        self.server_parameters
                    )
                )
            )

            session = (
                await exit_stack.enter_async_context(
                    ClientSession(
                        read_stream,
                        write_stream,
                    )
                )
            )

            await session.initialize() # poignee de main serveur client

        except Exception as error: # gestion erreurs
            await exit_stack.aclose()

            raise MCPClientError(
                f"Cannot connect to MCP server: {error}"
            ) from error

        self._exit_stack = exit_stack
        self._session = session



    async def close(self) -> None:
        """Close the session and stop the stdio server."""

        if self._exit_stack is not None:
            await self._exit_stack.aclose()

        self._session = None
        self._exit_stack = None



    def _get_session(self) -> ClientSession:
        """Return the active session or raise an error."""

        if self._session is None:
            raise MCPClientError(
                "MCP client is not connected"
            )

        return self._session



    async def list_tools(self) -> list[Tool]:
        """Return all tools exposed by the server."""

        session = self._get_session()
        result = await session.list_tools()

        return list(result.tools)



    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> str:
        """Call an MCP tool and return its text result."""

        session = self._get_session()

        result = await session.call_tool( # appel du tool "name"
            name,
            arguments,
        )

        text_parts = [ # extraction reponse
            block.text
            for block in result.content
            if isinstance(block, TextContent) # recuperation uniquement texte
        ]

        if text_parts:
            text_result = "\n".join(text_parts) # assemblages blocs textes
        elif result.structured_content is not None:
            text_result = json.dumps(
                result.structured_content,
                indent=2,
            )
        else:
            text_result = ""

        if result.is_error:
            raise MCPClientError(
                f"MCP tool '{name}' failed: "
                f"{text_result}"
            )

        return text_result # retour resultat



    async def build_tools_manual(self) -> str:
        """Build documentation for every available tool."""

        tools = await self.list_tools()

        sections = []

        for tool in tools:
            schema = json.dumps(
                tool.input_schema,
                indent=2,
            )

            section = (
                f"Tool: {tool.name}\n"
                f"Description: "
                f"{tool.description or 'No description'}\n"
                f"Input schema:\n{schema}"
            )

            sections.append(section)

        return "\n\n".join(sections)


    async def __aenter__(self) -> "StdioMCPClient":
        """Connect when entering an async with block."""

        await self.connect()
        return self


    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: object,
    ) -> None:
        """Close when leaving an async with block."""

        await self.close()