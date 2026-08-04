"""
scenario_demo.py
=================
سيناريو تجريبي عشان نثبت إن باقي الفلو (Appium MCP + Filesystem MCP +
الـ agents) شغال end-to-end، من غير ما نستنى Atlassian/Jira MCP.

بيستخدم test case يدوي جاهز في reports/test-cases/test_case_DEMO-1.json
بدل ما يجيبه من Jira، وبعدين يكمل نفس الفلو بالظبط:
execute -> handle_failures -> finalize_report

تشغيل:
    python scenario_demo.py
"""

import os
import json
import yaml
from pathlib import Path

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter

from mcp_servers import (
    APPIUM_MCP_SERVER,
    FILESYSTEM_MCP_SERVER,
    REPORTS_DIR,
    ANDROID_DEVICE_NAME,
    ANDROID_APP_PACKAGE,
)

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"

with open(CONFIG_DIR / "agents.yaml", "r", encoding="utf-8") as f:
    agents_cfg = yaml.safe_load(f)

with open(CONFIG_DIR / "tasks.yaml", "r", encoding="utf-8") as f:
    tasks_cfg = yaml.safe_load(f)

llm = LLM(
    model=f"openai/{os.getenv('NVIDIA_MODEL', 'z-ai/glm-5.2')}",
    base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=1,
    top_p=1,
    max_tokens=16384,
    seed=42,
)


def run_scenario():
    # هنا بس Appium + Filesystem (من غير Atlassian) عشان دي الحاجة اللي
    # عايزين نثبتها دلوقتي
    with MCPServerAdapter(
        [APPIUM_MCP_SERVER, FILESYSTEM_MCP_SERVER], connect_timeout=90
    ) as all_tools:

        def tools_for(*keywords):
            return [t for t in all_tools if any(k.lower() in t.name.lower() for k in keywords)]

        fs_tools = tools_for("file", "read", "write", "directory")
        appium_tools = tools_for("appium", "tap", "swipe", "screenshot", "record", "element")

        # ---------------------------------------------------------------
        # نفتح جلسة Appium إحنا بالكود مباشرة (مش عن طريق الـ LLM) عشان
        # نتجنب مشاكل تنسيق الـ JSON المتكررة، وبعدين نسيب الـ Agent
        # يكمل شغله على جلسة جاهزة ومفتوحة.
        # ---------------------------------------------------------------
        session_tool = next(t for t in all_tools if t.name == "appium_session_management")
        session_capabilities = json.dumps({
            "platformName": "Android",
            "appium:deviceName": ANDROID_DEVICE_NAME,
            "appium:appPackage": ANDROID_APP_PACKAGE,
            "appium:appActivity": ".MainActivity",
            "appium:noReset": True,
        })
        print(">>> Pre-creating Appium session directly (bypassing LLM formatting)...")
        session_result = session_tool.run(
            action="create",
            platform="android",
            capabilities=session_capabilities,
            remoteServerUrl="",
            sessionId="",
        )
        print(f">>> Session creation result: {session_result}")

        test_executor = Agent(config=agents_cfg["test_executor"], tools=appium_tools + fs_tools, llm=llm)
        failure_handler = Agent(config=agents_cfg["failure_handler"], tools=appium_tools + fs_tools, llm=llm)
        reporter = Agent(config=agents_cfg["reporter"], tools=fs_tools, llm=llm)

        execute_tests_task = Task(config=tasks_cfg["execute_tests_task"], agent=test_executor)
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
            agents=[test_executor, failure_handler, reporter],
            tasks=[execute_tests_task, handle_failures_task, finalize_report_task],
            process=Process.sequential,
            max_rpm=2,
            cache=False,
            verbose=True,
        )

        result = crew.kickoff(
            inputs={
                "reports_dir": REPORTS_DIR,
                "device_name": ANDROID_DEVICE_NAME,
                "app_package": ANDROID_APP_PACKAGE,
            }
        )
        return result


if __name__ == "__main__":
    os.makedirs(os.path.join(REPORTS_DIR, "test-cases"), exist_ok=True)
    print(">>> Running demo scenario (Jira skipped, using manual test case DEMO-1)...")
    output = run_scenario()
    print("\n=== Scenario Result ===\n")
    print(output)
    print(f"\nCheck {REPORTS_DIR}\\final_report.md for the output.")