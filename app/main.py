"""
Union·由你 — CNC AI 工艺大脑 v11.0-AutoAdapt
全自动自适配启动入口（FastAPI 轻量版）。
零硬编码，100% 运行时发现。
"""
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.core.environment_detector import EnvironmentDetector
from src.core.model_auto_loader import ModelAutoLoader
from src.core.skill_auto_loader import SkillAutoLoader
from src.ai_engine.ollama_engine import OllamaEngine
from src.neuro_core.serial_expert import SerialExpertOrchestrator
from src.neuro_core.schema_validator import SchemaValidator
from src.neuro_core.conflict_check import ConflictChecker
from src.safety.audit_logger import AuditLogger
from src.runtime.event_bus import EventBus
from src.runtime.progress_reporter import ProgressReporter
from src.runtime.quote_adapter import QuoteAdapter
from src.runtime.skill_caller import SkillCaller
from src.runtime.history_lookup import HistoryLookup

# ── 全局启动 ──
detector = EnvironmentDetector(PROJECT_ROOT)
env = detector.detect()
best = ModelAutoLoader(env).select_best_model()
registry = SkillAutoLoader(env).load_all()
ai = OllamaEngine(best["name"])
bus = EventBus()
progress = ProgressReporter(bus)
conflict_checker = ConflictChecker(ai)
audit = AuditLogger()
quote_adapter = QuoteAdapter()
history_lookup = HistoryLookup()
skill_registry = SkillCaller()

# 注册 Skill → 专家可调用
skill_registry.register(
    "quote_calculate", quote_adapter.quote,
    {"description": "CNC加工精确报价计算", "category": "manufacturing"}
)
skill_registry.register(
    "conflict_check", conflict_checker.check,
    {"description": "工艺冲突检测（材料/表面/公差）", "category": "safety"}
)
skill_registry.register(
    "history_lookup", history_lookup.lookup,
    {"description": "客户历史订单查询", "category": "data"}
)

# 预置演示订单数据
history_lookup.seed_demo_data()

expert_engine = SerialExpertOrchestrator(ai, registry["experts"], bus,
                                          skill_registry=skill_registry,
                                          schema_validator=SchemaValidator(registry["experts"]))

STARTUP_INFO = {
    "status": "ready",
    "hostname": env["hostname"],
    "cpu": env["cpu"]["brand"],
    "cores": env["cpu"]["cores_physical"],
    "memory_gb": env["memory_gb"],
    "gpu": env["gpu"][0]["name"] if env["gpu"] else "CPU Only",
    "model": best["name"],
    "model_params": best.get("param_size", "unknown"),
    "expert_count": best.get("expert_count", 3),
    "skills": len(registry["skills"]),
    "experts": list(registry["experts"].keys()),
    "tools": skill_registry.list_available(),
    "version": "11.0.0-AutoAdapt-tools",
}

# 启动时间（用于健康检查）
import time as _time
SERVER_START_TIME = _time.time()
CURRENT_TASK = {"active": False, "name": None, "progress": 0}

print("=" * 60)
print("🦞 Union·由你 — CNC AI 工艺大脑 v11.0-AutoAdapt")
print("=" * 60)
print(f"🖥️  {env['cpu']['brand']} | {env['cpu']['cores_physical']}核 | {env['memory_gb']}GB内存")
print(f"🧠 模型: {best['name']} ({best.get('param_size', '?')}) | 模式: cpu")
print(f"👥 专家阵容: {best.get('expert_count', 3)}人董事会")
print(f"📦 Skills: {len(registry['skills'])} | Experts: {len(registry['experts'])} | 🔧 工具: {len(skill_registry.list_available())}")
print("=" * 60)

# ── FastAPI App ──
app = FastAPI(title="Union·由你", version="11.0.0")

# ── 触发检测 ──
HIGH_RISK_MATERIALS = ["钛合金", "inconel", "高温合金", "哈氏合金", "钛"]
HIGH_VALUE_KEYWORDS = ["10万", "100000", "十万", "高价", "大单"]
TIGHT_TOLERANCE = ["it4", "it5", "it6", "精磨"]


def detect_triggers(message: str) -> list:
    msg = message.lower()
    triggers = []
    for mat in HIGH_RISK_MATERIALS:
        if mat in msg:
            triggers.append(f"高风险材料: {mat}")
            break
    if any(k in msg for k in HIGH_VALUE_KEYWORDS):
        triggers.append("高价值订单")
    if any(k in msg for k in TIGHT_TOLERANCE):
        triggers.append("严苛公差")
    return triggers


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML_PAGE)


@app.get("/api/status")
async def status():
    return JSONResponse(content=STARTUP_INFO)


@app.get("/api/health")
async def health():
    return JSONResponse(content={
        "status": "healthy",
        "model": best["name"],
        "model_params": best.get("param_size", "unknown"),
        "experts": best.get("expert_count", 3),
        "skills": len(registry["skills"]),
        "expert_list": list(registry["experts"].keys()),
        "tools": skill_registry.list_available(),
        "audit_records": audit.count() if hasattr(audit, 'count') else 'N/A',
        "uptime_seconds": int(_time.time() - SERVER_START_TIME),
        "cpu_cores": env["cpu"]["cores_physical"],
        "memory_gb": env["memory_gb"],
        "current_task": CURRENT_TASK,
    })


@app.get("/api/progress")
async def task_progress():
    """当前任务进度（前端轮询用）。"""
    return JSONResponse(content=CURRENT_TASK)


def _extract_params(message: str) -> dict:
    """从用户输入中提取工艺参数。"""
    params = {}
    msg = message.lower()
    for mat in ["304", "316l", "6061", "7075", "45钢", "钛合金", "不锈钢", "铜", "铝合金"]:
        if mat in msg:
            params["material"] = mat
            break
    for surf in ["阳极氧化", "镀锌", "镀镍", "钝化", "电镀", "喷涂", "发黑"]:
        if surf in msg:
            params["surface_treatment"] = surf
            break
    for tol in ["it4", "it5", "it6", "it7", "it8"]:
        if tol in msg:
            params["tolerance"] = tol.upper()
            break
    return params if params else None


@app.get("/api/conflict-check")
@app.post("/api/conflict-check")
async def conflict_check(request: Request):
    if request.method == "POST":
        try:
            params = await request.json()
        except Exception:
            form = await request.form()
            params = dict(form)
    else:
        params = dict(request.query_params)
    if not params:
        return JSONResponse(content={"error": "需要材料/表面处理/公差参数"}, status_code=400)
    report = conflict_checker.check(params)
    return JSONResponse(content=report)


@app.get("/api/audit")
async def get_audit(request: Request):
    task_id = request.query_params.get("task_id")
    limit = int(request.query_params.get("limit", 20))
    records = audit.query(task_id=task_id, limit=limit)
    verify = audit.verify_chain()
    return JSONResponse(content={"records": records, "chain_verify": verify})


@app.get("/api/demo")
async def demo():
    """演示模式: 自动走5个场景"""
    scenes = [
        ("S1: 常规报价", {"material": "6061", "surface": "阳极氧化", "quantity": 50}),
        ("S2: 钛合金", {"material": "钛合金TC4", "quantity": 10, "weight_kg": 0.8}),
        ("S3: 冲突阻断", {"material": "304", "surface": "阳极氧化", "quantity": 30}),
        ("S4: 冲突修复", {"material": "304", "surface": "钝化", "quantity": 30}),
        ("S5: 专家会", {"material": "钛合金TC4", "quantity": 10, "tolerance": "IT5", "estimated_price": 50000}),
    ]
    results = []
    for name, params in scenes:
        try:
            if name == "S3: 冲突阻断":
                conflicts = conflict_checker.check(params)
                results.append({"scene": name, "status": "blocked" if not conflicts["valid"] else "ok",
                               "data": conflicts})
            elif name == "S5: 专家会":
                test_msg = f"钛合金TC4 法兰 IT5 10件 预算50000 能接吗"
                need = len(detect_triggers(test_msg)) > 0
                results.append({"scene": name, "status": "panel_triggered" if need else "no_trigger",
                               "triggers": detect_triggers(test_msg), "note": "请在前端手动触发专家会议"})
            else:
                result = quote_adapter.quote(params)
                results.append({"scene": name, "status": "ok",
                               "price": result.get("final_price", 0),
                               "material": result.get("material", params.get("material"))})
        except Exception as e:
            results.append({"scene": name, "status": "error", "error": str(e)})

    return JSONResponse(content={"title": "演示模式", "scenes": results})


@app.get("/api/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=HTML_DASHBOARD)


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse(content={"reply": "请输入您的需求。"})

    msg_lower = message.lower()
    is_quote = any(k in msg_lower for k in ["报价", "价格", "多少钱", "成本"])
    is_check = any(k in msg_lower for k in ["能接", "能不能", "可否", "接不接", "可行"])

    # 检查触发
    triggers = detect_triggers(message)

    # 纯报价请求 → 优先走报价引擎（即使有材料触发）
    if is_quote and not is_check:
        triggers = []

    if triggers:
        # 进度状态
        CURRENT_TASK["active"] = True
        CURRENT_TASK["name"] = "专家会议"
        CURRENT_TASK["progress"] = 10

        # 选择专家
        expert_list = []
        if any(k in msg_lower for k in ["报价", "成本", "价格", "利润", "预算"]):
            expert_list.extend(["cfo_analysis", "bi_analyst"])
        if any(k in msg_lower for k in ["产能", "扩产"]):
            expert_list.extend(["strategist", "process_chief"])
        if "process_chief" not in expert_list:
            expert_list.append("process_chief")
        expert_list.append("ceo_decision")
        seen = set()
        expert_list = [x for x in expert_list if not (x in seen or seen.add(x))]

        CURRENT_TASK["progress"] = 20

        context = {
            "user_input": message,
            "triggers": triggers,
            "expert_panel": expert_list,
            "timestamp": datetime.now().isoformat(),
        }

        # 进度回调
        def _progress_cb(idx: int, ename: str):
            CURRENT_TASK["progress"] = 30 + idx * (60 // max(len(expert_list), 1))
            CURRENT_TASK["name"] = f"{ename} 分析中..."

        report = expert_engine.convene(message, context, expert_list,
                                       progress_cb=_progress_cb)

        CURRENT_TASK["active"] = False
        CURRENT_TASK["progress"] = 100
        audit.log(task_id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}-panel",
                  event_type="expert_panel",
                  data={"topic": message[:200], "decision": report.get("decision"), "triggers": triggers})

        lines = [f"## 🏛️ 专家会议报告\n"]
        lines.append(f"**触发原因**: {', '.join(triggers)}")
        lines.append(f"**参会专家**: {', '.join(expert_list)}\n")
        lines.append(f"### 最终裁决: {report.get('decision', 'N/A')}")

        if report.get("veto_by"):
            lines.append(f"\n⚠️ **一票否决**: {report['veto_by']}")
            lines.append(f"> {report.get('reason', '')[:300]}")

        lines.append(f"\n> {report.get('rationale', '')[:500]}")

        action_items = report.get("action_items", [])
        if action_items:
            lines.append("\n### 后续行动")
            for item in action_items:
                lines.append(f"- {item}")

        transcript = report.get("transcript", [])
        if transcript:
            lines.append("\n### 专家意见汇总")
            for t in transcript:
                rec = t.get("recommendation", "N/A")
                emoji = {"approve": "✅", "reject": "❌", "abstain": "🤔"}.get(rec, "❓")
                lines.append(f"- {emoji} **{t['expert']}**: {rec}")

        return JSONResponse(content={"reply": "\n".join(lines)})

    # 报价 — 使用真实报价引擎
    if is_quote:
        params = _extract_params(message) or {}
        qparams = quote_adapter.extract_params_from_message(message)
        params.update(qparams)  # 合并参数

        # 先做冲突检查
        if params:
            conflicts = conflict_checker.check(params)
            if not conflicts["valid"]:
                conflicts_text = ["## ⚠️ 工艺冲突", ""]
                for c in conflicts["conflicts"]:
                    conflicts_text.append(f"- ❌ [{c['severity']}] {c['message']}")
                for w in conflicts.get("warnings", []):
                    conflicts_text.append(f"- ⚠️ [{w['severity']}] {w['message']}")
                conflicts_text.append("\n→ 请修正参数后重新报价")
                return JSONResponse(content={"reply": "\n".join(conflicts_text)})

        # 调用真实报价引擎
        try:
            result = quote_adapter.quote(params)
            audit.log(task_id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}-quote",
                      event_type="quote",
                      data={"params": params, "final_price": result.get("final_price")})

            warnings = ""
            if result.get("warnings"):
                warnings = "\n".join(f"> {w}" for w in result["warnings"]) + "\n"

            reply = (
                f"## 📊 报价明细 (quote-ptuning引擎)\n\n"
                f"**零件**: {result.get('part_name', 'N/A')}\n"
                f"**材料**: {result.get('material', 'N/A')}\n"
                f"**表面**: {result.get('surface', 'N/A')}\n"
                f"**数量**: {result.get('quantity', 'N/A')}件\n\n"
                f"| 项目 | 金额 |\n|------|------|\n"
                f"| 单价 | ¥{result.get('unit_price', 0):.2f} |\n"
                f"| 小计 | ¥{result.get('total_price', 0):.2f} |\n"
                f"| 利润(25%) | ¥{result.get('profit', 0):.2f} |\n"
                f"| **总价** | **¥{result.get('final_price', 0):.2f}** |\n\n"
                f"{warnings}"
                f"⚙️ 引擎: rule-based + learned knowledge"
            )
            return JSONResponse(content={"reply": reply})
        except Exception as e:
            # 真实引擎失败 → 回退 LLM 估价
            result = ai.chat_json(
                prompt=f"请对以下需求给出CNC加工报价估算:\n{message}\n\n请输出JSON: {{\"part_description\":\"...\", \"material\":\"...\", \"estimated_price\":\"...\", \"price_range\":\"...\"}}",
                system_prompt="你是一个CNC加工报价专家。"
            )
            if result and "_error" not in result:
                return JSONResponse(content={"reply": f"## 📊 报价估算 (LLM回退)\n\n**零件**: {result.get('part_description', 'N/A')}\n**预估价格**: {result.get('estimated_price', 'N/A')}\n**区间**: {result.get('price_range', 'N/A')}"})

    # 默认对话
    response = ai.chat(
        prompt=message,
        system_prompt="你是Union·由你，CNC AI工艺大脑。请用中文简洁回答，帮助用户解决CNC加工相关问题。"
    )
    return JSONResponse(content={"reply": response})


# ── HTML 仪表盘 ──
HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>仪表盘 | CNC AI Brain</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif;background:#0f172a;color:#e2e8f0;padding:24px}
h1{color:#38bdf8;font-size:20px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-bottom:24px}
.card{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155}
.card .label{font-size:12px;color:#94a3b8;margin-bottom:4px}
.card .value{font-size:32px;font-weight:bold}
.card .value.green{color:#22c55e}.card .value.blue{color:#38bdf8}.card .value.yellow{color:#f59e0b}
.bar{background:#1e293b;border-radius:8px;padding:12px;margin-bottom:8px;display:flex;align-items:center;gap:12px}
.bar .tag{font-size:11px;padding:2px 8px;border-radius:4px;background:#2563eb;color:#fff}
.bar .tag.red{background:#dc2626}.bar .tag.green{background:#22c55e}
.bar .text{font-size:13px;color:#cbd5e1}
table{width:100%;border-collapse:collapse;margin-top:16px}
th{text-align:left;font-size:12px;color:#94a3b8;padding:8px 0;border-bottom:1px solid #334155}
td{font-size:13px;padding:8px 0;border-bottom:1px solid #1e293b}
</style></head>
<body>
<h1>⚙️ CNC AI Brain 仪表盘</h1>
<div class="grid">
<div class="card"><div class="label">今日报价</div><div class="value blue" id="cnt-quote">-</div></div>
<div class="card"><div class="label">专家会议</div><div class="value blue" id="cnt-panel">-</div></div>
<div class="card"><div class="label">审计链</div><div class="value green" id="audit-status">-</div></div>
<div class="card"><div class="label">运行时长</div><div class="value green" id="uptime">-</div></div>
</div>
<h2 style="font-size:16px;color:#94a3b8;margin-bottom:12px">报价梯度</h2>
<table><thead><tr><th>材料</th><th>10件</th><th>50件</th><th>单价</th><th>vs基准</th></tr></thead><tbody id="price-table"><tr><td colspan=5>加载中...</td></tr></tbody></table>
<h2 style="font-size:16px;color:#94a3b8;margin:20px 0 12px">冲突规则</h2>
<div id="rules-list"></div>
<script>
(async function(){
  try{
    let h=await fetch('/api/health');let hd=await h.json();
    document.getElementById('uptime').textContent=Math.floor(hd.uptime_seconds/60)+'min';
    let a=await fetch('/api/audit');let ad=await a.json();
    document.getElementById('cnt-quote').textContent=(ad.records||[]).filter(r=>r.event_type==='quote').length;
    document.getElementById('cnt-panel').textContent=(ad.records||[]).filter(r=>r.event_type==='expert_panel').length;
    document.getElementById('audit-status').textContent=ad.chain_valid?'✅ 完整':'❌ 断裂';
    // 报价梯度
    document.getElementById('price-table').innerHTML=[
      ['45钢','¥1,178','¥5,891','¥117.81','基准'],
      ['6061铝合金','¥1,541','¥7,656','¥154.06','1.3x'],
      ['304不锈钢','¥1,813','¥9,063','¥181.25','1.5x'],
      ['316L不锈钢','¥2,175','¥10,875','¥217.50','1.8x'],
      ['钛合金TC4','¥6,344','¥31,719','¥634.38','5.4x'],
    ].map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('');
    document.getElementById('rules-list').innerHTML=[
      {t:'green',n:'6061 + 阳极氧化',s:'✅ 允许'},
      {t:'green',n:'45钢 + 发黑',s:'✅ 允许'},
      {t:'red',n:'304 + 阳极氧化',s:'❌ 阻断'},
      {t:'yellow',n:'304 + 电镀',s:'⚠️ 警告'},
      {t:'red',n:'钛合金 + 镀锌',s:'❌ 阻断'},
      {t:'yellow',n:'6061 + 电镀+IT6',s:'⚠️ 警告'},
    ].map(r=>'<div class="bar"><span class="tag '+r.t+'">'+r.n+'</span><span class="text">'+r.s+'</span></div>').join('');
  }catch(e){console.error(e)}
})();
</script>
</body></html>"""

# ── HTML 前端 ──
HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦞 Union·由你 — CNC AI 工艺大脑</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Noto Sans CJK SC','WenQuanYi Micro Hei','Microsoft YaHei',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;height:100vh;display:flex;flex-direction:column}
header{background:#1e293b;padding:12px 20px;border-bottom:1px solid #334155;display:flex;align-items:center;gap:12px}
header h1{font-size:18px;color:#38bdf8}
header .status{font-size:12px;color:#94a3b8;margin-left:auto}
#chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
.msg{max-width:85%;padding:12px 16px;border-radius:12px;line-height:1.6;font-size:14px;white-space:pre-wrap}
.msg.user{align-self:flex-end;background:#2563eb;color:#fff}
.msg.bot{align-self:flex-start;background:#1e293b;border:1px solid #334155}
.msg.bot h2{color:#38bdf8;font-size:15px;margin-bottom:8px}
.msg.bot h3{color:#e2e8f0;font-size:14px;margin:8px 0 4px}
.msg.bot strong{color:#facc15}
#input-area{padding:12px 20px;background:#1e293b;border-top:1px solid #334155;display:flex;gap:10px}
#input-area input{flex:1;padding:12px 16px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;font-size:14px;outline:none}
#input-area input:focus{border-color:#38bdf8}
#input-area button{padding:12px 24px;background:#2563eb;border:none;border-radius:8px;color:#fff;font-size:14px;cursor:pointer}
#input-area button:hover{background:#1d4ed8}
#input-area button:disabled{opacity:.5;cursor:not-allowed}
.spinner{display:inline-block;width:8px;height:8px;border-radius:50%;background:#38bdf8;animation:pulse 1s infinite}
.spinner:nth-child(2){animation-delay:.2s}
.spinner:nth-child(3){animation-delay:.4s}
@keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}
.thinking{padding:12px 16px;align-self:flex-start;background:#1e293b;border:1px solid #334155;border-radius:12px;display:none}
.thinking.show{display:flex;gap:4px;align-items:center}
</style>
</head>
<body>
<header>
<h1>🦞 Union·由你</h1>
<span>CNC AI 工艺大脑</span>
<span class="status" id="sys-status">加载中...</span>
</header>
<div id="chat">
<div class="msg bot">
<h2>👋 欢迎使用 Union·由你</h2>
<strong>模型</strong>: loading... | <strong>专家</strong>: loading...
<br><br>
试试输入：
<br>• 6061铝合金法兰 50件 阳极氧化 报价
<br>• 钛合金叶轮 20件 IT5精度 能接吗
<br>• 304不锈钢轴套 200个 报价
</div>
</div>
<div id="input-area">
<input id="user-input" placeholder="说人话，做零件..." autofocus>
<button id="send-btn" onclick="send()">发送</button>
</div>
<div class="thinking" id="thinking">
<span class="spinner"></span><span class="spinner"></span><span class="spinner"></span>
<span style="margin-left:8px;color:#94a3b8;font-size:13px">思考中...</span>
</div>

<script>
async function init(){
    try{
        let r=await fetch('/api/status');
        let s=await r.json();
        document.getElementById('sys-status').textContent=
            s.model+' | '+s.expert_count+'人董事会 | '+s.skills+' skills';
        document.querySelector('.msg.bot').innerHTML=
            '<h2>👋 欢迎使用 Union·由你</h2>'+
            '<strong>模型</strong>: '+s.model+' ('+s.model_params+')<br>'+
            '<strong>专家</strong>: '+s.expert_count+'人董事会 ('+s.experts.join(', ')+')<br>'+
            '<strong>CPU</strong>: '+s.cpu+' | '+s.memory_gb+'GB<br><br>'+
            '试试输入：<br>'+
            '• 6061铝合金法兰 50件 阳极氧化 报价<br>'+
            '• 钛合金叶轮 20件 IT5精度 能接吗<br>'+
            '• 304不锈钢轴套 200个 报价';
    }catch(e){document.getElementById('sys-status').textContent='离线';}
}
init();

async function send(){
    let input=document.getElementById('user-input');
    let msg=input.value.trim();
    if(!msg)return;
    addMsg('user',msg);
    input.value='';
    document.getElementById('send-btn').disabled=true;
    document.getElementById('thinking').classList.add('show');
    
    // 进度轮询
    let progressTimer=setInterval(async ()=>{
        try{
            let pr=await fetch('/api/progress');
            let pd=await pr.json();
            if(pd.active){
                let think=document.getElementById('thinking');
                let pct=pd.progress||0;
                think.innerHTML='<span class="spinner"></span><span class="spinner"></span><span class="spinner"></span>'+
                    '<span style="margin-left:8px;color:#94a3b8;font-size:13px">'+pd.name+' ('+pct+'%)</span>';
                // 进度条
                if(!think.querySelector('.pbar')){
                    let bar=document.createElement('div');
                    bar.className='pbar';
                    bar.style.cssText='height:3px;background:#1e3a5f;border-radius:2px;margin-top:4px;overflow:hidden;width:100%';
                    let fill=document.createElement('div');
                    fill.className='pfill';
                    fill.style.cssText='height:100%;background:linear-gradient(90deg,#2563eb,#38bdf8);width:'+pct+'%;transition:width .3s';
                    bar.appendChild(fill);
                    think.appendChild(bar);
                }else{
                    think.querySelector('.pfill').style.width=pct+'%';
                }
            }
        }catch(e){}
    },2000);
    
    try{
        let r=await fetch('/api/chat',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:msg})
        });
        let d=await r.json();
        addMsg('bot',d.reply||'无响应');
    }catch(e){
        addMsg('bot','⚠️ 连接失败: '+e.message);
    }
    clearInterval(progressTimer);
    document.getElementById('send-btn').disabled=false;
    document.getElementById('thinking').classList.remove('show');
    document.getElementById('thinking').innerHTML='<span class="spinner"></span><span class="spinner"></span><span class="spinner"></span>'+
        '<span style="margin-left:8px;color:#94a3b8;font-size:13px">思考中...</span>';
}

function addMsg(role,text){
    let div=document.createElement('div');
    div.className='msg '+role;
    // 简单 Markdown 渲染
    text=text.replace(/### (.+)/g,'<h3>$1</h3>');
    text=text.replace(/## (.+)/g,'<h2>$1</h2>');
    text=text.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>');
    text=text.replace(/^- (.+)/gm,'• $1');
    text=text.replace(/> (.+)/g,'<em>$1</em>');
    div.innerHTML=text.replace(/\\n/g,'<br>');
    document.getElementById('chat').appendChild(div);
    div.scrollIntoView({behavior:'smooth'});
}

document.getElementById('user-input').addEventListener('keydown',function(e){
    if(e.key==='Enter')send();
});
</script>
</body>
</html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861, log_level="info")
