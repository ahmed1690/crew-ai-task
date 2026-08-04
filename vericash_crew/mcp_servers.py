"""
تعريف اتصالات الـ 3 MCP servers: Atlassian (Jira), Appium, Filesystem.
كل واحد بيرجع server params object تستخدمها MCPServerAdapter من crewai_tools.

توثيق مرجعي:
- crewai-tools MCP support: https://docs.crewai.com/en/mcp/overview
- Atlassian Remote MCP: https://www.atlassian.com/platform/remote-mcp-server
- Filesystem MCP (official): https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- Appium MCP: https://github.com/appium/mcp-server (أو أي implementation بديل متاح عندك)
"""

import os
from dotenv import load_dotenv
from mcp import StdioServerParameters

load_dotenv()

# ---------------------------------------------------------------------------
# 1) Atlassian MCP (Jira) — server بيتوصله عن طريق SSE (remote, بيحتاج OAuth
#    login أول مرة من المتصفح لما تشغل الكريو).
# ---------------------------------------------------------------------------
ATLASSIAN_MCP_SERVER = {
    "url": os.getenv("ATLASSIAN_MCP_URL", "https://mcp.atlassian.com/v1/mcp/authv2"),
    "transport": "streamable-http",
}

# ---------------------------------------------------------------------------
# 2) Appium MCP — server بيتشغل local عن طريق stdio (بيحتاج appium server
#    شغال + emulator شغال على نفس الجهاز).
# ---------------------------------------------------------------------------
APPIUM_MCP_SERVER = StdioServerParameters(
    command=os.getenv("APPIUM_MCP_COMMAND", "npx"),
    args=os.getenv("APPIUM_MCP_ARGS", "-y,appium-mcp").split(","),
    env={
        **os.environ,
        "APPIUM_SERVER_URL": os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723"),
    },
)

# ---------------------------------------------------------------------------
# 3) Filesystem MCP — server بيتشغل local عن طريق stdio، بيدّيله الـ dir
#    اللي مسموح يقرا/يكتب فيه بس (الـ reports dir).
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