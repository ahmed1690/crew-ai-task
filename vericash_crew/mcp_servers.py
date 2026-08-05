"""
Defines the connections for the 3 MCP servers: Atlassian (Jira), Appium,
and Filesystem. Each one returns a server params object used by
MCPServerAdapter from crewai_tools.

Reference docs:
- crewai-tools MCP support: https://docs.crewai.com/en/mcp/overview
- Atlassian Remote MCP: https://www.atlassian.com/platform/remote-mcp-server
- Filesystem MCP (official): https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- Appium MCP: https://github.com/appium/mcp-server (or any alternative implementation you have)
"""

import os
from dotenv import load_dotenv
from mcp import StdioServerParameters

load_dotenv()

# ---------------------------------------------------------------------------
# 1) Atlassian MCP (Jira) — connected via streamable-http (remote, requires
#    a one-time OAuth login in the browser when the crew is first run).
# ---------------------------------------------------------------------------
ATLASSIAN_MCP_SERVER = {
    "url": os.getenv("ATLASSIAN_MCP_URL", "https://mcp.atlassian.com/v1/mcp/authv2"),
    "transport": "streamable-http",
}

# ---------------------------------------------------------------------------
# 2) Appium MCP — run directly via node on the installed file (instead of
#    npx, to avoid any package-resolution overhead/delay). The default path
#    is built automatically from the current Windows username.
# ---------------------------------------------------------------------------
_default_appium_mcp_path = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Roaming", "npm", "node_modules", "appium-mcp", "dist", "index.js",
)

APPIUM_MCP_SERVER = StdioServerParameters(
    command=os.getenv("APPIUM_MCP_COMMAND", "node"),
    args=[os.getenv("APPIUM_MCP_SCRIPT_PATH", _default_appium_mcp_path)],
    env={
        **os.environ,
        "APPIUM_SERVER_URL": os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723"),
        "ANDROID_HOME": os.getenv("ANDROID_HOME", os.environ.get("ANDROID_HOME", "")),
    },
)

# ---------------------------------------------------------------------------
# 3) Filesystem MCP — run locally via stdio, given only the one directory
#    it's allowed to read/write (the reports dir).
# ---------------------------------------------------------------------------
FILESYSTEM_MCP_SERVER = StdioServerParameters(
    command=os.getenv("FILESYSTEM_MCP_COMMAND", "npx"),
    args=os.getenv(
        "FILESYSTEM_MCP_ARGS",
        f"-y,@modelcontextprotocol/server-filesystem,{os.getenv('REPORTS_DIR', './reports')}",
    ).split(","),
)

REPORTS_DIR = os.getenv("REPORTS_DIR", "./reports")
ANDROID_DEVICE_NAME = os.getenv("ANDROID_DEVICE_NAME", "emulator-5554")
ANDROID_APP_PACKAGE = os.getenv("ANDROID_APP_PACKAGE", "com.vericash.app")
ANDROID_APP_ACTIVITY = os.getenv("ANDROID_APP_ACTIVITY", ".MainActivity")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "VER")