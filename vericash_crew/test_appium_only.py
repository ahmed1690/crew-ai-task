"""اختبار عزل: يتأكد من MCP واحد بس (Appium) عشان نعرف هو المشكلة ولا لأ."""
from crewai_tools import MCPServerAdapter
from mcp_servers import APPIUM_MCP_SERVER

print(">>> Trying to connect to Appium MCP only...")
with MCPServerAdapter(APPIUM_MCP_SERVER) as tools:
    print(f">>> SUCCESS. Tools found: {[t.name for t in tools]}")
