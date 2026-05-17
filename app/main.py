"""
Union·由你 — CNC AI 工艺大脑 v11.0.4
全自动自适配 · 一句话画STEP+3D预览+上传报价+输出打包
作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统
"""
import sys, json, os, io
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
import uvicorn

from src.core.environment_detector import EnvironmentDetector
from src.core.model_auto_loader import ModelAutoLoader
from src.core.model_registry import ModelRegistry
from src.core.skill_auto_loader import SkillAutoLoader
from src.ai_engine.ollama_engine import OllamaEngine
from src.ai_engine.engine import AIEngine
from src.neuro_core.serial_expert import SerialExpertOrchestrator
from src.neuro_core.schema_validator import SchemaValidator
from src.neuro_core.conflict_check import ConflictChecker
from src.safety.audit_logger import AuditLogger
from src.runtime.event_bus import EventBus
from src.runtime.progress_reporter import ProgressReporter
from src.runtime.quote_adapter import QuoteAdapter
from src.runtime.skill_caller import SkillCaller
from src.runtime.history_lookup import HistoryLookup
from src.runtime.step_generator import generate_part, get_weight, DENSITY
from src.runtime.step_parser import extract_bbox_from_step, estimate_volume_from_bbox, get_material_density
from src.runtime.export_bundler import create_bundle

# ── Shadow Mode ──
def wrap_shadow(response: dict) -> dict:
    response["disclaimer"] = "此结论为AI建议，仅供参考。实际加工前请人工确认。"
    response["shadow_mode"] = True
    return response

# ── 全局启动 ──
detector = EnvironmentDetector(PROJECT_ROOT)
env = detector.detect()

# 模型注册表 — 自动检测Ollama + 云端配置
model_registry = ModelRegistry(PROJECT_ROOT / "config" / "models.json")
best_config = model_registry.select_best(min_quality=0)
if not best_config:
    best_config = ModelAutoLoader(env).select_best_model()

# 根据模型来源选择引擎
if best_config and best_config.get("source") == "cloud":
    ai = AIEngine(best_config)
elif best_config:
    ai = OllamaEngine(best_config["name"])
else:
    ai = OllamaEngine("qwen2.5:3b")  # 默认fallback

registry = SkillAutoLoader(env).load_all()
bus = EventBus()
progress = ProgressReporter(bus)
conflict_checker = ConflictChecker(ai)
audit = AuditLogger()
quote_adapter = QuoteAdapter()
history_lookup = HistoryLookup()
skill_registry = SkillCaller()

skill_registry.register("quote_calculate", quote_adapter.quote, {"description": "CNC加工精确报价计算"})
skill_registry.register("conflict_check", conflict_checker.check, {"description": "工艺冲突检测"})
skill_registry.register("history_lookup", history_lookup.lookup, {"description": "客户历史订单查询"})
history_lookup.seed_demo_data()

expert_engine = SerialExpertOrchestrator(ai, registry["experts"], bus,
    skill_registry=skill_registry, schema_validator=SchemaValidator(registry["experts"]))

STARTUP_INFO = {
    "status": "ready", "hostname": env["hostname"],
    "cpu": env["cpu"]["brand"], "cores": env["cpu"]["cores_physical"],
    "memory_gb": env["memory_gb"],
    "gpu": env["gpu"][0]["name"] if env["gpu"] else "CPU Only",
    "model": best_config["name"] if best_config else "unknown",
    "model_source": best_config.get("source", "ollama") if best_config else "unknown",
    "model_params": best_config.get("param_size", best_config.get("param_count", "unknown")) if best_config else "unknown",
    "model_provider": best_config.get("provider", "ollama") if best_config else "none",
    "expert_count": best_config.get("expert_count", 3) if best_config else 3,
    "skills": len(registry["skills"]), "experts": list(registry["experts"].keys()),
    "tools": skill_registry.list_available(), "version": "11.0.4",
}

import time as _time
SERVER_START_TIME = _time.time()
CURRENT_TASK = {"active": False, "name": None, "progress": 0}

print("=" * 60)
print("🦞 Union·由你 — CNC AI 工艺大脑 v11.0.4")
print("  一句话画图·3D预览·上传报价·输出打包")
print("=" * 60)
if best_config:
    src = best_config.get("source", "?")
    prov = best_config.get("provider", "?")
    print(f"🤖 模型: {best_config['name']} ({src}/{prov})")
    if src == "cloud":
        print(f"☁️  云端: {best_config.get('api_url', '?')}")
    else:
        print(f"💻 本地: {best_config.get('size_gb', '?')}GB")
print("=" * 60)
print(f"🖥️  {env['cpu']['brand']} | {env['cpu']['cores_physical']}核 | {env['memory_gb']}GB")
print(f"🧠 模型: {best_config['name'] if best_config else 'none'} | 👥 {best_config.get('expert_count', 3) if best_config else 3}人董事会")
print(f"📐 STEP生成: trimesh | 🎨 3D预览: Three.js | 📦 ZIP打包: 就绪")
print("=" * 60)

app = FastAPI(title="Union·由你", version="11.0.4")

# ── 触发检测 ──
HIGH_RISK_MATERIALS = ["钛合金", "inconel", "高温合金", "哈氏合金", "钛"]
HIGH_VALUE_KEYWORDS = ["10万", "100000", "十万", "高价", "大单"]
TIGHT_TOLERANCE = ["it4", "it5", "it6", "精磨"]

def detect_triggers(message: str) -> list:
    msg = message.lower()
    triggers = []
    for mat in HIGH_RISK_MATERIALS:
        if mat in msg: triggers.append(f"高风险材料: {mat}"); break
    if any(k in msg for k in HIGH_VALUE_KEYWORDS): triggers.append("高价值订单")
    if any(k in msg for k in TIGHT_TOLERANCE): triggers.append("严苛公差")
    return triggers

# ── API: 根页面/状态/健康 ──
@app.get("/", response_class=HTMLResponse)
async def index(): return HTMLResponse(content=HTML_PAGE)

@app.get("/api/status")
async def status(): return JSONResponse(content=STARTUP_INFO)

@app.get("/api/health")
async def health():
    return JSONResponse(content={
        "status": "healthy",
        "model": best_config["name"] if best_config else "none",
        "model_source": best_config.get("source", "none") if best_config else "none",
        "model_params": best_config.get("param_size", best_config.get("param_count", "unknown")) if best_config else "unknown",
        "experts": best_config.get("expert_count", 3) if best_config else 3,
        "skills": len(registry["skills"]),
        "expert_list": list(registry["experts"].keys()),
        "tools": skill_registry.list_available(),
        "audit_records": audit.count() if hasattr(audit, 'count') else 'N/A',
        "uptime_seconds": int(_time.time() - SERVER_START_TIME),
        "cpu_cores": env["cpu"]["cores_physical"],
        "memory_gb": env["memory_gb"],
        "current_task": CURRENT_TASK,
        "version": "11.0.4",
        "model_provider": best_config.get("provider", "none") if best_config else "none",
    })

@app.get("/api/version")
async def version(): return JSONResponse(content={"version": "11.0.4", "codename": "工业炼金术师"})

@app.get("/api/models")
async def list_models():
    all_m = model_registry.get_all_ranked()
    return JSONResponse(content={
        "total": len(all_m),
        "best": best_config,
        "models": [{"name": m["name"], "source": m["source"], "score": m["quality_score"],
                     "provider": m.get("provider", "?")} for m in all_m],
        "config_path": str(model_registry.config_path),
    })

@app.get("/api/progress")
async def task_progress(): return JSONResponse(content=CURRENT_TASK)

# ── API: 冲突检测 / 审计 ──
@app.get("/api/conflict-check")
@app.post("/api/conflict-check")
async def conflict_check(request: Request):
    if request.method == "POST":
        try: params = await request.json()
        except: params = dict(await request.form())
    else: params = dict(request.query_params)
    if not params: return JSONResponse(content={"error": "需要参数"}, status_code=400)
    return JSONResponse(content=conflict_checker.check(params))

@app.get("/api/audit")
async def get_audit(request: Request):
    task_id = request.query_params.get("task_id")
    limit = int(request.query_params.get("limit", 20))
    return JSONResponse(content={"records": audit.query(task_id=task_id, limit=limit),
                                 "chain_verify": audit.verify_chain()})

# ── ★ API: 一句话画STEP ──
@app.post("/api/generate-step")
async def generate_step(request: Request):
    try: params = await request.json()
    except: return JSONResponse(content={"error": "需要JSON参数"}, status_code=400)
    
    part_type = params.get("part_type", params.get("type", "flange"))
    result = generate_part(part_type, params)
    if "error" in result: return JSONResponse(content=result, status_code=400)
    
    audit.log(task_id=f"step-{os.urandom(3).hex()}", event_type="step_generate", data=params)
    return JSONResponse(content=result)

# ── ★ API: 3D预览 (STL文件服务) ──
@app.get("/api/preview/{filename}")
async def preview_stl(filename: str):
    stl_path = PROJECT_ROOT / "data" / "step" / filename
    if not stl_path.exists():
        return JSONResponse(content={"error": "文件不存在"}, status_code=404)
    return FileResponse(stl_path, media_type="application/octet-stream")

# ── ★ API: 上传STEP报价 ──
@app.post("/api/upload-step")
async def upload_step_quote(file: UploadFile = File(...), material: str = Form("6061"),
                            quantity: int = Form(10), surface: str = Form("无")):
    # 保存上传文件
    upload_dir = PROJECT_ROOT / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    
    # STEP解析
    bbox = extract_bbox_from_step(str(file_path))
    if not bbox or "error" in bbox:
        return JSONResponse(content={"error": "STEP解析失败，请确认文件格式", "detail": bbox}, status_code=400)
    
    # 体积/重量估算
    volume_mm3 = estimate_volume_from_bbox(bbox)
    volume_cm3 = volume_mm3 / 1000
    density = get_material_density(material)
    weight_kg = (volume_cm3 * density) / 1000
    
    # 报价
    quote_params = {
        "material": material, "surface_treatment": surface,
        "quantity": quantity, "weight_kg": round(weight_kg, 3),
        "bounding_box": [bbox["dim_x"], bbox["dim_y"], bbox["dim_z"]],
    }
    
    # 冲突检查
    conflicts = conflict_checker.check({"material": material, "surface": surface})
    
    # 调用报价引擎
    quote_result = quote_adapter.quote(quote_params) if conflicts["valid"] else None
    
    result = {
        "file_name": file.filename,
        "bounding_box": {"x": bbox["dim_x"], "y": bbox["dim_y"], "z": bbox["dim_z"]},
        "volume_mm3": round(volume_mm3, 0),
        "volume_cm3": round(volume_cm3, 2),
        "material": material, "density_g_cm3": density,
        "estimated_weight_kg": round(weight_kg, 3),
        "conflicts": conflicts,
        "quote": quote_result,
        "disclaimer": "包围盒 × 实体率 估算，实际重量以加工后称重为准。此结论为AI建议，仅供参考。",
        "shadow_mode": True,
    }
    audit.log(task_id=f"upload-{os.urandom(3).hex()}", event_type="step_upload_quote", data=result)
    return JSONResponse(content=result)

# ── ★ API: 输出打包 ──
@app.post("/api/export")
async def export_bundle(request: Request):
    try: params = await request.json()
    except: return JSONResponse(content={"error": "需要JSON参数"}, status_code=400)
    
    task_id = params.get("task_id", os.urandom(4).hex())
    files = params.get("files", [])
    quote_data = params.get("quote")
    metadata = params.get("metadata", {"task_id": task_id, "created": datetime.now().isoformat()})
    
    files_exist = [f for f in files if os.path.exists(f.get("path", ""))]
    result = create_bundle(task_id, files_exist, quote_data, metadata)
    audit.log(task_id=task_id, event_type="export", data=result)
    return JSONResponse(content=result)

# ── ★ API: 下载ZIP ──
@app.get("/api/download/{filename}")
async def download_zip(filename: str):
    zip_path = PROJECT_ROOT / "data" / "exports" / filename
    if not zip_path.exists():
        return JSONResponse(content={"error": "文件不存在"}, status_code=404)
    return FileResponse(zip_path, media_type="application/zip", filename=filename)

# ── ★ API: 一句话全链路 ──
@app.post("/api/one-click")
async def one_click(request: Request):
    """输入JSON参数 → 生成STEP+报价+打包ZIP，返回完整结果"""
    try: params = await request.json()
    except: return JSONResponse(content={"error": "需要JSON参数"}, status_code=400)
    
    part_type = params.get("part_type", "flange")
    material = params.get("material", "6061")
    quantity = params.get("quantity", 10)
    surface = params.get("surface", "无")
    
    results = {"pipeline": [], "step": 0}
    
    # Step1: 生成STEP
    gen_result = generate_part(part_type, params)
    if "error" in gen_result:
        return JSONResponse(content={"error": f"STEP生成失败: {gen_result['error']}"}, status_code=400)
    results["pipeline"].append({"step": "generate", "status": "ok", "data": gen_result})
    results["step"] = 1
    
    # Step2: 冲突检测
    conflicts = conflict_checker.check({"material": material, "surface": surface})
    results["pipeline"].append({"step": "conflict_check", "status": "ok", "data": conflicts})
    results["step"] = 2
    
    # Step3: 报价
    quote_params = {"material": material, "surface_treatment": surface, "quantity": quantity}
    if "volume_cm3" in gen_result:
        quote_params["weight_kg"] = round(get_weight(material, gen_result["volume_cm3"]) / 1000, 3)
    
    if conflicts["valid"]:
        quote_result = quote_adapter.quote(quote_params)
        results["pipeline"].append({"step": "quote", "status": "ok", "data": quote_result})
    else:
        quote_result = None
        conflict_msgs = [c["message"] for c in conflicts.get("conflicts", [])]
        results["pipeline"].append({"step": "quote", "status": "blocked", "reason": "; ".join(conflict_msgs)})
    results["step"] = 3
    
    # Step4: 打包 (有文件且无冲突)
    if gen_result.get("step_file") and quote_result:
        bundle_files = [
            {"path": gen_result["step_file"], "name": f"{part_type}.step"},
        ]
        if gen_result.get("stl_file"):
            bundle_files.append({"path": gen_result["stl_file"], "name": f"{part_type}.stl"})
        
        bundle = create_bundle(os.urandom(4).hex(), bundle_files,
                               quote_data={"material": material, "quantity": quantity,
                                          "surface_treatment": surface,
                                          "unit_price": quote_result.get("unit_price"),
                                          "total_price": quote_result.get("final_price")},
                               metadata={"part_type": part_type, "params": params})
        results["pipeline"].append({"step": "export", "status": "ok", "data": bundle})
        results["zip_url"] = bundle.get("zip_url")
    results["step"] = 4
    
    # Step5: 3D预览URL
    if gen_result.get("stl_url"):
        results["preview_url"] = gen_result["stl_url"]
    
    results["disclaimer"] = "此结论为AI建议，仅供参考。实际加工前请人工确认。"
    results["shadow_mode"] = True
    results["version"] = "11.0.4"
    
    audit.log(task_id=f"oneclick-{os.urandom(4).hex()}", event_type="one_click", data={"params": params, "pipeline_count": len(results["pipeline"])})
    return JSONResponse(content=results)

# ── API: 演示 ──
@app.get("/api/demo")
async def demo():
    scenes = [
        ("S1: STEP生成", "generate"),
        ("S2: 常规报价", "quote"),
        ("S3: 冲突阻断", "conflict"),
        ("S4: 上传STEP报价", "upload"),
        ("S5: 专家会议", "panel"),
    ]
    results = []
    for name, stype in scenes:
        try:
            if stype == "generate":
                r = generate_part("flange", {"od": 100, "id": 50, "thickness": 20})
                results.append({"scene": name, "status": "ok" if "error" not in r else "error",
                               "preview": r.get("stl_url", ""), "bbox": r.get("bounding_box_mm", [])})
            elif stype == "quote":
                r = quote_adapter.quote({"material": "6061", "surface_treatment": "阳极氧化", "quantity": 50})
                results.append({"scene": name, "status": "ok", "price": r.get("final_price", 0)})
            elif stype == "conflict":
                r = conflict_checker.check({"material": "304", "surface": "阳极氧化", "quantity": 30})
                results.append({"scene": name, "status": "blocked" if not r["valid"] else "ok", "data": r})
            elif stype == "upload":
                results.append({"scene": name, "status": "api_ready",
                               "endpoint": "POST /api/upload-step (multipart)"})
            elif stype == "panel":
                triggers = detect_triggers("钛合金TC4 IT5 预算50000 能接吗")
                results.append({"scene": name, "status": "panel_triggered" if triggers else "no_trigger",
                               "triggers": triggers})
        except Exception as e:
            results.append({"scene": name, "status": "error", "error": str(e)})
    return JSONResponse(content={"title": "v11.0.4 演示模式", "scenes": results})

# ── API: 仪表盘 ──
@app.get("/api/dashboard", response_class=HTMLResponse)
async def dashboard(): return HTMLResponse(content=HTML_DASHBOARD)

# ── 对话 ──
@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message: return JSONResponse(content=wrap_shadow({"reply": "请输入您的需求。"}))

    msg_lower = message.lower()
    is_quote = any(k in msg_lower for k in ["报价", "价格", "多少钱", "成本"])
    is_check = any(k in msg_lower for k in ["能接", "能不能", "可否", "接不接", "可行"])
    is_draw = any(k in msg_lower for k in ["画", "生成", "建模", "创建"]) and any(
        k in msg_lower for k in ["法兰", "轴套", "轴", "齿轮", "箱体", "支架", "板", "法兰盖", "闷盖"])

    triggers = detect_triggers(message)
    if is_quote and not is_check: triggers = []

    if is_draw:
        # 尝试提取零件类型和参数
        part_type = "flange"
        for pt in ["法兰", "轴套", "轴", "箱体", "支架", "板", "方块"]:
            if pt in message:
                part_type = {"法兰": "flange", "轴套": "sleeve", "轴": "shaft", "箱体": "box",
                            "支架": "bracket", "板": "plate", "方块": "box"}.get(pt, "flange")
                break
        # 参数提取（简化版）
        import re
        params = {"od": 100, "id": 50, "thickness": 20}  # 默认法兰
        od_m = re.search(r'外径\s*(\d+)', message) or re.search(r'od\s*(\d+)', msg_lower)
        id_m = re.search(r'内径\s*(\d+)', message) or re.search(r'id\s*(\d+)', msg_lower)
        th_m = re.search(r'厚\s*(\d+)', message) or re.search(r'厚度\s*(\d+)', msg_lower)
        if od_m: params["od"] = int(od_m.group(1))
        if id_m: params["id"] = int(id_m.group(1))
        if th_m: params["thickness"] = int(th_m.group(1))
        
        gen = generate_part(part_type, params)
        if "error" in gen:
            return JSONResponse(content=wrap_shadow({"reply": f"❌ {gen['error']}"}))
        
        bbox = gen.get("bounding_box_mm", [100, 100, 20])
        preview = gen.get("stl_url", "")
        reply = (
            f"## 📐 STEP已生成\n\n"
            f"**类型**: {part_type}\n"
            f"**尺寸**: {bbox[0]}×{bbox[1]}×{bbox[2]} mm\n"
            f"**体积**: {gen.get('volume_cm3', '-')} cm³\n"
            f"**预估重量(6061)**: {gen.get('estimated_weight_g', '-')} g\n"
            f"[🎨 3D预览]({preview})\n"
            f"STEP文件: `{gen.get('step_file', '')}`"
        )
        return JSONResponse(content=wrap_shadow({"reply": reply, "step_file": gen.get("step_file"),
                                                  "stl_url": preview}))

    if triggers:
        CURRENT_TASK.update(active=True, name="专家会议", progress=10)
        expert_list = []
        if any(k in msg_lower for k in ["报价", "成本", "价格", "利润", "预算"]):
            expert_list.extend(["cfo_analysis", "bi_analyst"])
        if any(k in msg_lower for k in ["产能", "扩产"]):
            expert_list.extend(["strategist", "process_chief"])
        if "process_chief" not in expert_list: expert_list.append("process_chief")
        expert_list.append("ceo_decision")
        expert_list = list(dict.fromkeys(expert_list))
        CURRENT_TASK["progress"] = 20

        def _progress_cb(idx, ename):
            CURRENT_TASK["progress"] = 30 + idx * (60 // max(len(expert_list), 1))
            CURRENT_TASK["name"] = f"{ename} 分析中..."

        report = expert_engine.convene(message,
            {"user_input": message, "triggers": triggers, "expert_panel": expert_list,
             "timestamp": datetime.now().isoformat()},
            expert_list, progress_cb=_progress_cb)

        CURRENT_TASK.update(active=False, progress=100)
        audit.log(task_id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}-panel",
                  event_type="expert_panel",
                  data={"topic": message[:200], "decision": report.get("decision"), "triggers": triggers})

        lines = [f"## 🏛️ 专家会议报告\n**触发**: {', '.join(triggers)}\n**参会**: {', '.join(expert_list)}\n"]
        lines.append(f"### 最终裁决: {report.get('decision', 'N/A')}")
        if report.get("veto_by"):
            lines.append(f"\n⚠️ **一票否决**: {report['veto_by']}\n> {report.get('reason', '')[:300]}")
        lines.append(f"\n> {report.get('rationale', '')[:500]}")
        transcript = report.get("transcript", [])
        if transcript:
            lines.append("\n### 专家意见")
            for t in transcript:
                emoji = {"approve": "✅", "reject": "❌", "abstain": "🤔"}.get(t.get("recommendation"), "❓")
                lines.append(f"- {emoji} **{t['expert']}**: {t.get('recommendation', 'N/A')}")
        lines.append("\n> ⚠️ 此结论为AI建议，仅供参考。实际加工前请人工确认。")
        return JSONResponse(content=wrap_shadow({"reply": "\n".join(lines)}))

    if is_quote:
        params = quote_adapter.extract_params_from_message(message)
        if params:
            conflicts = conflict_checker.check(params)
            if not conflicts["valid"]:
                conflicts_text = ["## ⚠️ 工艺冲突"]
                for c in conflicts["conflicts"]:
                    conflicts_text.append(f"- ❌ [{c['severity']}] {c['message']}")
                for w in conflicts.get("warnings", []):
                    conflicts_text.append(f"- ⚠️ [{w['severity']}] {w['message']}")
                conflicts_text.append("\n→ 请修正参数后重新报价")
                return JSONResponse(content=wrap_shadow({"reply": "\n".join(conflicts_text)}))

        result = quote_adapter.quote(params or {})
        audit.log(task_id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}-quote",
                  event_type="quote", data={"params": params, "final_price": result.get("final_price")})
        warnings = "\n".join(f"> {w}" for w in result.get("warnings", [])) if result.get("warnings") else ""
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
            f"{warnings}\n> ⚠️ 此结论为AI建议，仅供参考"
        )
        return JSONResponse(content=wrap_shadow({"reply": reply}))

    response = ai.chat(prompt=message,
        system_prompt="你是Union·由你，CNC AI工艺大脑。请用中文简洁回答CNC加工问题。")
    return JSONResponse(content=wrap_shadow({"reply": response}))

# ── HTML 仪表盘 ──
HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>仪表盘 | CNC AI Brain v11.0.4</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif;background:#0f172a;color:#e2e8f0;padding:24px}
h1{color:#38bdf8;font-size:20px;margin-bottom:4px}
.sub{color:#94a3b8;font-size:12px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px}
.card{background:#1e293b;border-radius:12px;padding:16px;border:1px solid #334155}
.card .label{font-size:11px;color:#94a3b8;margin-bottom:4px}
.card .value{font-size:28px;font-weight:bold}
.card .value.green{color:#22c55e}.card .value.blue{color:#38bdf8}.card .value.yellow{color:#f59e0b}
.bar{background:#1e293b;border-radius:8px;padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
.bar .tag{font-size:10px;padding:2px 8px;border-radius:4px;background:#2563eb;color:#fff}
.bar .tag.red{background:#dc2626}.bar .tag.green{background:#22c55e}.bar .tag.yellow{background:#f59e0b}
.bar .text{font-size:13px;color:#cbd5e1}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}
th{text-align:left;font-size:11px;color:#94a3b8;padding:6px 0;border-bottom:1px solid #334155}
td{padding:6px 0;border-bottom:1px solid #1e293b}
.api-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-top:10px}
.api-item{background:#1e293b;border-radius:8px;padding:10px;font-size:12px}
.api-item .method{color:#38bdf8;font-weight:bold}
.api-item .path{color:#cbd5e1;font-family:monospace;font-size:11px}
h2{font-size:15px;margin:20px 0 10px;color:#94a3b8}
</style></head>
<body>
<h1>⚙️ CNC AI Brain v11.0.4</h1>
<div class="sub">一句话画STEP + 3D预览 + 上传报价 + 输出打包</div>
<div class="grid">
<div class="card"><div class="label">今日报价</div><div class="value blue" id="cnt-quote">-</div></div>
<div class="card"><div class="label">专家会议</div><div class="value blue" id="cnt-panel">-</div></div>
<div class="card"><div class="label">STEP生成</div><div class="value yellow" id="cnt-step">-</div></div>
<div class="card"><div class="label">审计链</div><div class="value green" id="audit-status">-</div></div>
<div class="card"><div class="label">运行时长</div><div class="value green" id="uptime">-</div></div>
</div>
<h2>📐 报价梯度</h2>
<table><thead><tr><th>材料</th><th>10件</th><th>50件</th><th>单价</th><th>倍率</th></tr></thead><tbody id="price-table"></tbody></table>
<h2>🔒 冲突规则</h2>
<div id="rules-list"></div>
<h2>🔌 API 端点 (v11.0.4 新增)</h2>
<div class="api-grid" id="api-list"></div>
<script>
(async function(){
  try{
    let h=await fetch('/api/health'),hd=await h.json();
    document.getElementById('uptime').textContent=Math.floor(hd.uptime_seconds/60)+'min';
    let a=await fetch('/api/audit'),ad=await a.json();
    document.getElementById('cnt-quote').textContent=(ad.records||[]).filter(r=>r.event_type==='quote').length;
    document.getElementById('cnt-panel').textContent=(ad.records||[]).filter(r=>r.event_type==='expert_panel').length;
    document.getElementById('cnt-step').textContent=(ad.records||[]).filter(r=>r.event_type==='step_generate').length;
    document.getElementById('audit-status').textContent=ad.chain_valid?'✅':'❌';
    document.getElementById('price-table').innerHTML=[
      ['45钢','¥1,178','¥5,891','¥117.81','基准'],
      ['6061铝合金','¥1,541','¥7,656','¥154.06','1.3x'],
      ['304不锈钢','¥1,813','¥9,063','¥181.25','1.5x'],
      ['316L不锈钢','¥2,175','¥10,875','¥217.50','1.8x'],
      ['钛合金TC4','¥6,344','¥31,719','¥634.38','5.4x'],
    ].map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('');
    document.getElementById('rules-list').innerHTML=[
      ['green','6061+阳极氧化','✅'],
      ['green','45钢+发黑','✅'],
      ['red','304+阳极氧化','❌'],
      ['yellow','304+电镀','⚠️'],
      ['red','钛合金+镀锌','❌'],
      ['yellow','6061+电镀+IT6','⚠️'],
    ].map(r=>'<div class="bar"><span class="tag '+r[0]+'">'+r[1]+'</span><span class="text">'+r[2]+'</span></div>').join('');
    document.getElementById('api-list').innerHTML=[
      ['POST','/api/generate-step','一句话画STEP'],
      ['GET','/api/preview/{file}','3D预览(STL)'],
      ['POST','/api/upload-step','上传STEP自动报价'],
      ['POST','/api/export','输出打包(ZIP)'],
      ['POST','/api/one-click','全链路一键'],
      ['GET','/api/download/{file}','下载ZIP'],
    ].map(r=>'<div class="api-item"><span class="method">'+r[0]+'</span> <span class="path">'+r[1]+'</span><br><span style="font-size:10px;color:#64748b">'+r[2]+'</span></div>').join('');
  }catch(e){console.error(e)}
})();
</script>
</body></html>"""

# ── HTML 3D预览主页面 ──
HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🦞 Union·由你 — CNC AI 工艺大脑 v11.0.4</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Noto Sans CJK SC','WenQuanYi Micro Hei','Microsoft YaHei',sans-serif;background:#0f172a;color:#e2e8f0;height:100vh;display:flex}
.sidebar{width:360px;display:flex;flex-direction:column;background:#1e293b;border-right:1px solid #334155}
.sidebar header{padding:12px 16px;background:#0f172a;border-bottom:1px solid #334155}
.sidebar header h1{font-size:16px;color:#38bdf8}
.sidebar header .ver{font-size:11px;color:#64748b}
#chat{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:92%;padding:10px 14px;border-radius:10px;line-height:1.5;font-size:13px}
.msg.user{align-self:flex-end;background:#2563eb;color:#fff}
.msg.bot{align-self:flex-start;background:#1e293b;border:1px solid #334155}
.msg.bot h2{color:#38bdf8;font-size:14px;margin-bottom:6px}
.msg.bot h3{font-size:13px;margin:6px 0 3px}
.msg.bot a{color:#38bdf8}
.msg.bot strong{color:#facc15}
#input-area{padding:10px 14px;background:#0f172a;border-top:1px solid #334155;display:flex;gap:8px}
#input-area input{flex:1;padding:10px 14px;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#e2e8f0;font-size:13px;outline:none}
#input-area input:focus{border-color:#38bdf8}
#input-area button{padding:10px 18px;background:#2563eb;border:none;border-radius:8px;color:#fff;font-size:13px;cursor:pointer;white-space:nowrap}
#input-area button:hover{background:#1d4ed8}
#input-area button:disabled{opacity:.5}
#viewer{flex:1;background:#000;position:relative;display:flex;align-items:center;justify-content:center}
#viewer-placeholder{color:#475569;font-size:15px;text-align:center}
#viewer-placeholder .icon{font-size:64px;margin-bottom:16px}
.spinner{display:inline-block;width:8px;height:8px;border-radius:50%;background:#38bdf8;animation:pulse 1s infinite}
.spinner:nth-child(2){animation-delay:.2s}.spinner:nth-child(3){animation-delay:.4s}
@keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}
.upload-zone{margin:8px 14px;padding:20px;border:2px dashed #334155;border-radius:10px;text-align:center;cursor:pointer;font-size:12px;color:#94a3b8;transition:border-color .2s}
.upload-zone:hover{border-color:#38bdf8}
.upload-zone input{display:none}
.quick-actions{display:flex;gap:6px;padding:0 14px 10px;flex-wrap:wrap}
.quick-actions button{padding:6px 12px;background:#1e293b;border:1px solid #334155;border-radius:6px;color:#cbd5e1;font-size:11px;cursor:pointer}
.quick-actions button:hover{background:#2563eb;border-color:#2563eb}
</style>
</head>
<body>
<div class="sidebar">
<header><h1>🦞 Union·由你</h1><div class="ver">v11.0.4 工业炼金术师</div></header>
<div class="quick-actions">
<button onclick="quickGen('flange')">🔩 法兰</button>
<button onclick="quickGen('sleeve')">🔧 轴套</button>
<button onclick="quickGen('plate')">📏 平板</button>
<button onclick="quickGen('bracket')">📐 支架</button>
<button onclick="quickGen('box')">📦 箱体</button>
</div>
<div id="chat">
<div class="msg bot">
<h2>👋 一句话工业炼金术师</h2>
3D预览 + 画图 + 报价 + ZIP打包<br><br>
试试：<br>
• 画一个法兰 外径120内径60厚25<br>
• 6061法兰 50件 报价<br>
• 上传STEP文件自动报价<br>
• 钛合金IT5 预算5万 能接吗
</div></div>
<div class="upload-zone" onclick="document.getElementById('file-upload').click()" id="drop-zone">
  📁 拖拽或点击上传 STEP/STL 文件 (自动报价)
  <input type="file" id="file-upload" accept=".step,.stp,.stl" onchange="uploadFile(this.files[0])">
</div>
<div id="input-area">
<input id="user-input" placeholder="说人话，做零件..." autofocus>
<button id="send-btn" onclick="send()">发送</button>
</div>
</div>
<div id="viewer">
<div id="viewer-placeholder">
<div class="icon">📐</div>
在左侧生成或上传STEP<br>3D模型将在此处显示
</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/three@0.160/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.160/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.160/examples/js/loaders/STLLoader.js"></script>

<script>
// 3D 查看器
let scene,camera,renderer,controls,currentMesh;
function initViewer(){
    scene=new THREE.Scene();scene.background=new THREE.Color(0x1a1a2e);
    camera=new THREE.PerspectiveCamera(45,document.getElementById('viewer').clientWidth/document.getElementById('viewer').clientHeight,1,1000);
    camera.position.set(150,120,180);camera.lookAt(0,0,0);
    renderer=new THREE.WebGLRenderer({antialias:true});
    renderer.setSize(document.getElementById('viewer').clientWidth,document.getElementById('viewer').clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    document.getElementById('viewer').appendChild(renderer.domElement);
    controls=new THREE.OrbitControls(camera,renderer.domElement);
    controls.enableDamping=true;controls.dampingFactor=0.05;
    // 光照
    scene.add(new THREE.AmbientLight(0x404060));
    let dl=new THREE.DirectionalLight(0xffffff,1);dl.position.set(1,1,1);scene.add(dl);
    let dl2=new THREE.DirectionalLight(0x4488ff,0.6);dl2.position.set(-1,-1,-0.5);scene.add(dl2);
    // 网格
    let grid=new THREE.GridHelper(200,20,0x333355,0x222233);
    scene.add(grid);
    animate();
}
function animate(){
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene,camera);
}
function loadSTL(url){
    if(!scene){initViewer();}
    let loader=new THREE.STLLoader();
    loader.load(url,function(geo){
        if(currentMesh)scene.remove(currentMesh);
        geo.computeVertexNormals();
        let mat=new THREE.MeshPhongMaterial({color:0x4488cc,specular:0x111111,shininess:30,transparent:true,opacity:0.85});
        currentMesh=new THREE.Mesh(geo,mat);
        // 居中
        geo.computeBoundingBox();
        let center=geo.boundingBox.getCenter(new THREE.Vector3());
        currentMesh.position.sub(center);
        scene.add(currentMesh);
        document.getElementById('viewer-placeholder').style.display='none';
    },undefined,function(err){
        document.getElementById('viewer-placeholder').innerHTML='<div class="icon">⚠️</div>3D加载失败<br>请重试';
    });
}

// 快捷生成
async function quickGen(type){
    let input=document.getElementById('user-input');
    let defaults={flange:'画一个外径100内径50厚20的法兰',sleeve:'画一个外径60内径30长100的轴套',
                  plate:'画一个150x100x10的平板',bracket:'画一个80x60x8长100的L型支架',
                  box:'画一个长100宽80高60的箱体'};
    input.value=defaults[type]||'';
    send();
}

async function send(){
    let input=document.getElementById('user-input'),msg=input.value.trim();
    if(!msg)return;
    addMsg('user',msg);input.value='';
    document.getElementById('send-btn').disabled=true;
    try{
        let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
        let d=await r.json();
        addMsg('bot',d.reply||'无响应');
        // 如果有STEP文件,自动加载3D
        if(d.stl_url){loadSTL(d.stl_url);}
    }catch(e){addMsg('bot','⚠️ '+e.message);}
    document.getElementById('send-btn').disabled=false;
}

async function uploadFile(file){
    if(!file)return;
    addMsg('user','📁 上传: '+file.name+' (分析中...)');
    let form=new FormData();form.append('file',file);
    form.append('material',prompt('材料(默认6061):','6061')||'6061');
    form.append('quantity',prompt('数量(默认10):','10')||'10');
    form.append('surface',prompt('表面处理(默认无):','无')||'无');
    try{
        let r=await fetch('/api/upload-step',{method:'POST',body:form});
        let d=await r.json();
        if(d.error){addMsg('bot','❌ '+d.error);return;}
        let reply='## 📊 STEP上传报价\n\n';
        reply+='**文件**: '+d.file_name+'\n';
        reply+='**包围盒**: '+d.bounding_box.x+'×'+d.bounding_box.y+'×'+d.bounding_box.z+' mm\n';
        reply+='**体积**: '+d.volume_cm3+' cm³\n';
        reply+='**预估重量**: '+d.estimated_weight_kg+' kg\n';
        if(d.quote){
            reply+='\n| 项目 | 金额 |\n|------|------|\n';
            reply+='| 总价 | ¥'+d.quote.final_price+' |\n';
        }
        reply+='\n> ⚠️ '+d.disclaimer;
        addMsg('bot',reply);
    }catch(e){addMsg('bot','⚠️ '+e.message);}
}

function addMsg(role,text){
    let div=document.createElement('div');div.className='msg '+role;
    text=text.replace(/### (.+)/g,'<h3>$1</h3>').replace(/## (.+)/g,'<h2>$1</h2>');
    text=text.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>');
    text=text.replace(/> (.+)/g,'<em style="color:#94a3b8">$1</em>');
    div.innerHTML=text.replace(/\\n/g,'<br>');
    document.getElementById('chat').appendChild(div);
    div.scrollIntoView({behavior:'smooth'});
}

// 拖拽上传
let dz=document.getElementById('drop-zone');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.style.borderColor='#38bdf8'});
dz.addEventListener('dragleave',()=>dz.style.borderColor='#334155');
dz.addEventListener('drop',e=>{e.preventDefault();dz.style.borderColor='#334155';
    let f=e.dataTransfer.files[0];if(f)uploadFile(f);});

document.getElementById('user-input').addEventListener('keydown',function(e){if(e.key==='Enter')send();});
window.addEventListener('resize',()=>{if(renderer){let v=document.getElementById('viewer');
    camera.aspect=v.clientWidth/v.clientHeight;camera.updateProjectionMatrix();
    renderer.setSize(v.clientWidth,v.clientHeight);}});

// 懒启动3D引擎
document.getElementById('viewer').addEventListener('mouseenter',function(){
    if(!scene)initViewer();
},{once:true});
</script>
</body>
</html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861, log_level="info")
