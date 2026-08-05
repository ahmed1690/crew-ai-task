"""
vericash test-automation crew
==============================
CrewAI crew that runs the automated test flow as shown in the diagram:
Jira -> structure -> execute on emulator -> handle failures -> report

Run:
    python crew.py

Requirements: .env configured (copy from .env.example) + the 3 MCP
servers able to run (see README.md).
"""

import os
import yaml
from pathlib import Path

from crewai import Agent, Task, Crew, Process, LLM
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai_tools import MCPServerAdapter

from mcp_servers import (
    ATLASSIAN_MCP_SERVER,
    APPIUM_MCP_SERVER,
    FILESYSTEM_MCP_SERVER,
    REPORTS_DIR,
    ANDROID_DEVICE_NAME,
    ANDROID_APP_PACKAGE,
    JIRA_PROJECT_KEY,
)

# ---------------------------------------------------------------------------
# LLM: NVIDIA API (OpenAI-compatible endpoint) — base_url and model are
# read from .env; no secret is hardcoded here in the code.
# ---------------------------------------------------------------------------
llm = LLM(
    model=f"openai/{os.getenv('NVIDIA_MODEL', 'z-ai/glm-5.2')}",
    base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=1,
    top_p=1,
    max_tokens=16384,
    seed=42,
)

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"

with open(CONFIG_DIR / "agents.yaml", "r", encoding="utf-8") as f:
    agents_cfg = yaml.safe_load(f)

with open(CONFIG_DIR / "tasks.yaml", "r", encoding="utf-8") as f:
    tasks_cfg = yaml.safe_load(f)

# The "skill files" from the diagram = a Knowledge source read from the
# knowledge/ folder. Put any .md/.txt files there with extra guidance
# (e.g. how to handle vericash specifically, or conventions for test
# cases).
knowledge_sources = []
knowledge_dir = BASE_DIR / "knowledge"
if knowledge_dir.exists() and any(knowledge_dir.iterdir()):
    knowledge_sources = [
        TextFileKnowledgeSource(file_paths=[p.name for p in knowledge_dir.glob("*.md")])
    ]


def build_crew():
    # Opens a connection to all 3 MCP servers together; the tools come
    # back as one combined list and each agent gets the tools it needs
    # from it.
    with MCPServerAdapter(
        [ATLASSIAN_MCP_SERVER, APPIUM_MCP_SERVER, FILESYSTEM_MCP_SERVER], connect_timeout=90
    ) as all_tools:

        def tools_for(*keywords):
            """Filter tools whose name contains any of these keywords."""
            return [t for t in all_tools if any(k.lower() in t.name.lower() for k in keywords)]

        jira_tools = tools_for("jira", "atlassian", "issue")
        fs_tools = tools_for("file", "read", "write", "directory")
        appium_tools = tools_for("appium", "tap", "swipe", "screenshot", "record", "element")

        test_case_fetcher = Agent(config=agents_cfg["test_case_fetcher"], tools=jira_tools, llm=llm)
        test_structurer = Agent(config=agents_cfg["test_structurer"], tools=fs_tools, llm=llm)
        test_executor = Agent(config=agents_cfg["test_executor"], tools=appium_tools + fs_tools, llm=llm)
        failure_handler = Agent(config=agents_cfg["failure_handler"], tools=appium_tools + fs_tools, llm=llm)
        reporter = Agent(config=agents_cfg["reporter"], tools=fs_tools, llm=llm)

        fetch_test_cases_task = Task(config=tasks_cfg["fetch_test_cases_task"], agent=test_case_fetcher)
        structure_test_cases_task = Task(
            config=tasks_cfg["structure_test_cases_task"],
            agent=test_structurer,
            context=[fetch_test_cases_task],
        )
        execute_tests_task = Task(
            config=tasks_cfg["execute_tests_task"],
            agent=test_executor,
            context=[structure_test_cases_task],
        )
        handle_failures_task = Task(
            config=tasks_cfg["handle_failures_task"],
            agent=failure_handler,
            context=[execute_tests_task],
        )
        finalize_report_task = Task(
            config=tasks_cfg["finalize_report_task"],
            agent=reporter,
            context=[execute_tests_task, handle_failures_task],
        )

        crew = Crew(
            agents=[test_case_fetcher, test_structurer, test_executor, failure_handler, reporter],
            tasks=[
                fetch_test_cases_task,
                structure_test_cases_task,
                execute_tests_task,
                handle_failures_task,
                finalize_report_task,
            ],
            process=Process.sequential,
            knowledge_sources=knowledge_sources,
            max_rpm=3,
            verbose=True,
        )

        result = crew.kickoff(
            inputs={
                "project_key": JIRA_PROJECT_KEY,
                "reports_dir": REPORTS_DIR,
                "device_name": ANDROID_DEVICE_NAME,
                "app_package": ANDROID_APP_PACKAGE,
            }
        )
        return result


if __name__ == "__main__":
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output = build_crew()
    print("\n=== Final Report Summary ===\n")
    print(output)