import textwrap

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Weather Information",
    instructions=textwrap.dedent(
        """
        # Weather Information

        Provides information on current weather.
        """
    ),
)


@mcp.tool(
    description=textwrap.dedent(
        """
        Gets the current weather for the user.

        This tool is already aware of the user's location, so you don't need to provide it.
        """
    )
)
async def current_weather():
    return "Sunny, 27 degrees (C)."


if __name__ == "__main__":
    mcp.run()
