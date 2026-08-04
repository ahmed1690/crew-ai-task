# vericash CrewAI Test Automation

فلو آلي: يجيب test cases من Jira → ينفذهم على vericash app جوة Android
emulator عبر Appium → يحفظ الأدلة (screenshots/recordings) والتقرير
النهائي عن طريق Filesystem MCP.

## 1. تثبيت المتطلبات

```bash
python -m venv .venv
source .venv/bin/activate   # على ويندوز: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

عبّي ملف `.env` بالـ API key بتاع الموديل (OpenAI أو Anthropic) وبالإعدادات
اللي تحت.

## 2. تظبيط MCP servers الثلاثة (لسه مش متظبطين عندك)

### أ) Atlassian MCP (Jira)
Atlassian بتقدّم remote MCP server رسمي، مفيش حاجة تتثبت محليًا:
1. في `.env` سيب `ATLASSIAN_MCP_URL` زي ما هي (`https://mcp.atlassian.com/v1/sse`).
2. حط `ATLASSIAN_SITE_URL` و `JIRA_PROJECT_KEY` بتاعين شركتك.
3. أول ما تشغل `crew.py`، هيفتحلك تبويب متصفح لعمل OAuth login على
   Atlassian — ده بيحصل مرة واحدة بس (الـ token بيتخزن محليًا).
4. تأكد إن الـ Jira project فيه صلاحية قراءة للـ account اللي هتعمل بيه login.

### ب) Filesystem MCP
ده الـ official server من Anthropic/MCP، بيتشغل local عن طريق npx:
```bash
npm install -g @modelcontextprotocol/server-filesystem   # اختياري، أو سيبه لـ npx يحمله وقت التشغيل
```
في `.env`، `FILESYSTEM_MCP_ARGS` لازم يشاور على مجلد `reports/` بالظبط
(هو ده الحد اللي السيرفر مسموح يقرا/يكتب فيه — أمان).

### ج) Appium MCP
محتاج appium server + emulator شغالين الأول:
```bash
npm install -g appium
appium driver install uiautomator2
appium &                     # يفضل شغال في terminal منفصل

# شغل الـ emulator بتاعك (من Android Studio أو):
emulator -avd <avd_name> &

# ثبّت تطبيق vericash على الـ emulator (لو مش متثبت):
adb install path/to/vericash.apk
```
بعدين ثبّت الـ MCP server بتاع Appium (استخدمت `@appium/mcp-server` كمثال
— لو الشركة عندها implementation تاني داخلي، بدّل `APPIUM_MCP_ARGS` في
`.env` باسمه):
```bash
npm install -g @appium/mcp-server
```
تأكد إن `ANDROID_DEVICE_NAME` في `.env` مطابق للـ emulator id
(`adb devices` يوريك الاسم الصح، غالبًا `emulator-5554`).

## 3. اختبار سريع إن كل MCP شغال لوحده

```bash
# Filesystem
npx -y @modelcontextprotocol/server-filesystem ./reports

# Appium (تأكد إن appium و الـ emulator شغالين قبلها)
npx -y @appium/mcp-server
```
لو الاتنين اتشغلوا من غير error، يبقى تمام وننتقل للخطوة اللي بعدها.

## 4. حط "skill files" (اختياري)

أي ملاحظات إضافية عايز الـ crew يعرفها (مثلاً conventions خاصة بـ
vericash، أو حالات edge معينة) حطها كـ `.md` files جوة `knowledge/`،
وهتتحمل تلقائيًا كـ knowledge source.

## 5. تشغيل الكريو

```bash
python crew.py
```

النتيجة النهائية هتلاقيها في:
- `reports/test-cases/` → الـ test cases بعد التحويل لـ JSON
- `reports/<test_case_id>/` → screenshot أو recording لكل test case
- `reports/final_report.md` → التقرير الشامل

## بنية المشروع

```
vericash_crew/
├── crew.py                # نقطة التشغيل الرئيسية
├── mcp_servers.py          # تعريف اتصالات الـ 3 MCP servers
├── config/
│   ├── agents.yaml         # تعريف الـ 5 agents
│   └── tasks.yaml          # تعريف الـ 5 tasks بالترتيب
├── knowledge/               # "skill files" (اختياري)
├── reports/                 # مخرجات التنفيذ (auto-generated)
├── requirements.txt
└── .env.example
```

## ملاحظات مهمة

- الأسماء اللي استخدمتها لأدوات MCP (`jira`, `file`, `appium`...) في
  `crew.py` (دالة `tools_for`) لازم تتأكد إنها matching فعلاً مع أسماء
  الأدوات اللي كل MCP server بيرجعها عندك — شغّل `print([t.name for t in
  all_tools])` أول مرة عشان تشوف الأسماء الحقيقية وتظبط الفلترة لو
  محتاجة تعديل.
- `@appium/mcp-server` هو مثال شائع؛ لو مش متاح أو الشركة عندها MCP
  داخلي لـ Appium، بس بدّل `APPIUM_MCP_COMMAND`/`APPIUM_MCP_ARGS`.
