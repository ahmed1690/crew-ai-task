"""اختبار عزل: يتأكد من MCP واحد بس (Filesystem) عشان نعرف هو المشكلة ولا لأ."""
from crewai_tools import MCPServerAdapter
from mcp_servers import FILESYSTEM_MCP_SERVER

print(">>> Trying to connect to Filesystem MCP only...")
with MCPServerAdapter(FILESYSTEM_MCP_SERVER) as tools:
    print(f">>> SUCCESS. Tools found: {[t.name for t in tools]}")
