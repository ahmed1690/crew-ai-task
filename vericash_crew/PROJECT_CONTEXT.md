# VeriCash CrewAI — Full Project Context (AI Handoff Knowledge File)

> Purpose of this file: paste it into any AI assistant so it instantly understands the
> entire project — architecture, files, how to run, known bugs, and how to extend it.
> Keep it updated when the project changes.

---

## 1. One-line summary

A **CrewAI multi-agent pipeline** that automates mobile QA for the *VeriCash* Android
app. Flow: **fetch test cases from Jira → structure them into JSON → execute them on an
Android emulator via Appium → record/handle failures → write a final Markdown report** —
all driven by an LLM and three MCP servers (Atlassian, Appium, Filesystem).

---

## 2. Tech stack

- **Orchestration**: CrewAI (`crewai`, `crewai-tools[mcp]`), sequential `Process`.
- **LLM**: NVIDIA API, OpenAI-compatible endpoint (`https://integrate.api.nvidia.com/v1`).
  Model set in `.env` (`NVIDIA_MODEL`). Called through CrewAI's `LLM` wrapper as
  `openai/<model>`.
- **Tools via MCP (Model Context Protocol)** — 3 servers:
  1. **Atlassian MCP** (Jira) — remote, `streamable-http`, one-time browser OAuth.
  2. **Appium MCP** — local Node process, drives the emulator (tap/gesture/screenshot/record).
  3. **Filesystem MCP** — local `npx` server, read/write limited to the `reports/` dir.
- **Language runtime**: Python 3 (crew) + Node/npm (two MCP servers) + Appium server + Android SDK/emulator.
- **Config-as-data**: agents and tasks defined in YAML, loaded at runtime.

---

## 3. Directory layout

```
crew-ai-task/
└── vericash_crew/
    ├── crew.py              # MAIN entry — full 5-agent / 5-task pipeline (incl. Jira)
    ├── scenario_demo.py     # DEMO entry — skips Jira, runs Appium+FS on a manual test case
    ├── mcp_servers.py        # Defines the 3 MCP server connection params (reads .env)
    ├── config/
    │   ├── agents.yaml       # 5 agent definitions (role/goal/backstory)
    │   └── tasks.yaml        # 5 task definitions (description/expected_output), ordered
    ├── knowledge/            # OPTIONAL "skill files" (.md) auto-loaded as CrewAI knowledge — may not exist yet
    ├── reports/              # OUTPUT (auto-generated)
    │   ├── test-cases/       #   structured test_case_<id>.json files
    │   ├── <test_case_id>/   #   per-case evidence: success.png / retry_recording.mp4
    │   ├── final_report.md   #   the aggregated final report
    │   ├── execution_log.txt #   step-by-step log (written by scenario_demo.py callback)
    │   └── full_log_*.txt    #   captured terminal runs (UTF-16 console dumps)
    ├── test_llm.py           # Isolation test: does the NVIDIA LLM respond?
    ├── test_appium_only.py   # Isolation test: does the Appium MCP connect + list tools?
    ├── test_fs_only.py       # Isolation test: does the Filesystem MCP connect + list tools?
    ├── requirements.txt      # crewai / crewai-tools[mcp] / mcp / python-dotenv
    ├── .env                  # REAL secrets + config (NOT committed — see security note)
    ├── .env.example          # Template for .env
    └── README.md             # Setup notes (written in Arabic/Egyptian + English)
```

---

## 4. The pipeline — 5 agents, 5 tasks (sequential, each feeds the next)

Defined in `config/agents.yaml` + `config/tasks.yaml`, wired in `crew.py`.
Each agent only gets the MCP tools it needs (filtered by name via `tools_for(*keywords)`).

| # | Agent (role) | Task | Tools | What it does |
|---|---|---|---|---|
| 1 | `test_case_fetcher` (Jira Test Case Fetcher) | `fetch_test_cases_task` | Jira/Atlassian | Pull all test cases for project `{project_key}` from Jira as raw text |
| 2 | `test_structurer` (Test Case Structurer) | `structure_test_cases_task` | Filesystem | Convert each raw case to JSON `{id,title,preconditions,steps[],expected_result}`, save to `reports/test-cases/test_case_<id>.json` |
| 3 | `test_executor` (Appium Test Executor) | `execute_tests_task` | Appium + Filesystem | For each JSON case, drive the app on the emulator step by step, compare to expected, screenshot on pass / record on fail |
| 4 | `failure_handler` (Failure Recovery Agent) | `handle_failures_task` | Appium + Filesystem | Re-run failed cases, capture video evidence, document exact failing step |
| 5 | `reporter` (Test Report Finalizer) | `finalize_report_task` | Filesystem | Aggregate everything into `reports/final_report.md` (pass/fail totals + evidence links) |

**Task context chaining** (output of earlier task passed to later one):
`fetch → structure → execute → handle_failures → finalize`
(`finalize` receives both `execute` and `handle_failures` outputs).

**Runtime inputs** passed to `crew.kickoff(inputs=...)`, substituted into the YAML `{placeholders}`:
`project_key`, `reports_dir`, `device_name`, `app_package`.

---

## 5. Two entry points

- **`crew.py`** — the real thing. Connects all 3 MCP servers, runs all 5 agents including
  the Jira fetch. Use when Atlassian OAuth + Jira project are ready.
- **`scenario_demo.py`** — proof-of-life. **Skips Jira**, connects only Appium + Filesystem,
  and starts from a pre-written manual test case (`reports/test-cases/test_case_DEMO-1.json`).
  It contains the hard-won workarounds that `crew.py` does not yet have (see §7).

---

## 6. Key implementation details worth knowing

- **LLM config** (`crew.py` / `scenario_demo.py`): `model=openai/<NVIDIA_MODEL>`,
  `base_url` + `api_key` from env, `max_tokens=16384`, `seed=42`. `crew.py` uses
  `temperature=1`; the demo uses `0.2` (more deterministic for tool-calling).
- **Tool filtering**: `tools_for(*keywords)` matches MCP tool names by substring
  (`"jira"`, `"file"`, `"appium"`, …). **The real MCP tool names must actually contain
  these substrings** or an agent gets zero tools. Verify once with
  `print([t.name for t in all_tools])`.
- **MCP connection**: `MCPServerAdapter([...], connect_timeout=90)` as a context manager;
  all tools come back as one combined list, then get filtered per agent.
- **Knowledge sources**: if `knowledge/` exists and is non-empty, all `*.md` in it load as
  a `TextFileKnowledgeSource`. This is the intended place for VeriCash-specific conventions.
- **Rate limiting**: `max_rpm=3` (`crew.py`) / `2` (demo) to stay within API limits.
- **The Appium `null`-param problem** (documented in `scenario_demo.py`): CrewAI builds a
  pydantic schema from the MCP inputSchema; omitted optional params serialize as `null`,
  which the Appium MCP's `zod .optional()` rejects. The demo patches every tool's `_run`
  to strip `None`/`""` kwargs (`sanitize_tool`). Every agent backstory and task also
  screams "OMIT optional params, never send null/empty-string" for the same reason.
- **Appium session pre-creation** (demo only): the session is created *directly in Python*
  (not by the LLM) via the `appium_session_management` tool with explicit capabilities,
  then the executor agent is told the session/app is already open and to start interacting
  immediately. This avoids the LLM mangling the session-create JSON.
- **Appium tool whitelist** (demo): only
  `appium_screenshot, appium_gesture, appium_perform_actions, appium_screen_recording`
  are exposed to the executor. A loose `"appium"` keyword would also pull
  `appium_generate_tests / appium_ai / appium_session_management / appium_app_lifecycle`,
  which confuse the agent.
- **Coordinate-first tapping**: tasks instruct the executor to tap by explicit (x,y) when
  the step provides coordinates, instead of `find_element` — faster and more reliable.

---

## 7. Current status & known issues (read before running)

- **Last recorded run did NOT execute the test** (`reports/final_report.md`): the DEMO-1
  case was never run, `reports/DEMO-1/` was empty, no Appium session was active. So the
  end-to-end Appium execution is not yet confirmed green.
- **PATH MISMATCH BUG in `.env`**: `REPORTS_DIR` and `FILESYSTEM_MCP_ARGS` point to
  `D:\vericash_crew\vericash_crew\reports`, but the project actually lives at
  `D:\intern proj\crew-ai-task\vericash_crew\`. Fix `.env` to point at the real
  `...\crew-ai-task\vericash_crew\reports` (or move the project). Mismatched paths mean the
  Filesystem MCP writes/reads a different folder than you inspect.
- **Appium MCP path in `.env`** hardcodes user `ahmed`
  (`C:\Users\ahmed\AppData\Roaming\npm\...appium-mcp\dist\index.js`) and
  `ANDROID_HOME=C:\Users\ahmed\...`. On a different machine/user these paths break — update
  them to the actual install path (`npm root -g` finds global node_modules).
- **Model drift**: code default is `z-ai/glm-5.2`, `.env` sets
  `meta/llama-3.1-70b-instruct`, README/.env.example mention OpenAI/Anthropic. The `.env`
  value wins at runtime. Pick one deliberately.
- **`crew.py` lacks the demo's fixes**: it does NOT sanitize null params, does NOT
  whitelist Appium tools, and does NOT pre-create the session. Port those from
  `scenario_demo.py` before expecting `crew.py`'s execute stage to work reliably.
- **Atlassian OAuth**: first `crew.py` run opens a browser for a one-time login; the token
  is cached locally. Needs a Jira account with read access to project `VER`.
- **SECURITY**: `.env` currently contains a live NVIDIA API key committed inside the project
  tree. Treat it as compromised — rotate it, and make sure `.gitignore` excludes `.env`.

---

## 8. How to run

Prereqs installed once: Python 3, Node/npm, Appium (`npm i -g appium` +
`appium driver install uiautomator2`), Android SDK + an emulator/AVD, and the app installed
on the device.

```bash
# from vericash_crew/
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # then edit .env with real values + FIX THE PATHS (see §7)
```

Sanity checks (run each; all must pass before the full crew):
```bash
python test_llm.py            # LLM reachable?
python test_fs_only.py        # Filesystem MCP connects + lists tools?
python test_appium_only.py    # Appium MCP connects + lists tools? (needs appium + emulator up)
```

Bring up device stack (separate terminals):
```bash
appium                        # Appium server on 127.0.0.1:4723
emulator -avd <avd_name>      # or start it from Android Studio
adb devices                   # confirm the id matches ANDROID_DEVICE_NAME in .env
```

Run:
```bash
python scenario_demo.py       # SAFE first run — no Jira, uses DEMO-1, proves Appium+FS+agents
python crew.py                # FULL pipeline incl. Jira (after Atlassian OAuth is set up)
```

Outputs land in `reports/`: `test-cases/*.json`, `<id>/success.png|retry_recording.mp4`,
`final_report.md`, and (demo) `execution_log.txt`.

---

## 9. How to customize / extend

- **Add or edit test steps (no Jira)**: drop a `test_case_<id>.json` into
  `reports/test-cases/` shaped like DEMO-1 (`id,title,preconditions,steps[],expected_result`)
  and run `scenario_demo.py`.
- **Change agent behavior/personality**: edit `config/agents.yaml`
  (`role` / `goal` / `backstory`). No code change needed.
- **Change what a step does or its output contract**: edit `config/tasks.yaml`
  (`description` / `expected_output`). `{placeholders}` are filled from `kickoff(inputs=...)`.
- **Swap the LLM / model**: change `NVIDIA_MODEL` (and base_url/key) in `.env`, or point to
  OpenAI/Anthropic by editing the `LLM(...)` block. Keep the `openai/` prefix only for
  OpenAI-compatible endpoints.
- **Add project-specific guidance the agents should always follow**: create `knowledge/`
  and add `.md` files (e.g. VeriCash screen conventions, common edge cases). They auto-load.
- **Target a different app / device**: set `ANDROID_APP_PACKAGE`, `ANDROID_APP_ACTIVITY`,
  `ANDROID_DEVICE_NAME` in `.env`.
- **Add / remove an agent or task**: add its YAML block, then instantiate the `Agent`/`Task`
  in `crew.py` (or `scenario_demo.py`), add it to the `Crew(agents=[...], tasks=[...])`
  lists, and wire `context=[...]` to chain outputs.
- **Fix tool filtering** if an agent gets no tools: print the real MCP tool names and adjust
  the keywords in `tools_for(...)` (or use an exact-name whitelist like the demo does).

---

## 10. Glossary for the AI reading this

- **CrewAI**: framework for orchestrating multiple LLM "agents" that each own a role and
  execute "tasks" in a defined process (here, sequential).
- **Agent**: an LLM persona (role/goal/backstory) equipped with a set of tools.
- **Task**: a unit of work with a description + expected output, assigned to one agent, and
  optionally fed the outputs of prior tasks via `context`.
- **MCP (Model Context Protocol)**: a standard that exposes external capabilities (Jira,
  Appium, filesystem) as callable tools the LLM can invoke. `MCPServerAdapter` bridges MCP
  tools into CrewAI.
- **Appium**: automation server that controls real/emulated mobile apps (taps, gestures,
  screenshots, recordings).
- **VeriCash**: the Android app under test (`com.vericash.product_consumer_internal`).

---

*Generated as an AI-handoff context file. If the code changes, update §4–§9 so any future
AI (or teammate) gets an accurate picture in one paste.*
