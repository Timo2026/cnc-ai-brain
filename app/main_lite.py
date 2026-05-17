"""Union·由你 — CNC AI 工艺大脑 v11.0.4 Lite
零外部依赖版 (无需Ollama/无AI对话/无专家会议)
报价·画STEP·3D预览·上传·冲突·打包 完整可用
作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统"""
import sys, os, json, re, uuid
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

from src.runtime.step_generator import generate_part, PART_GENERATORS
from src.runtime.step_parser import extract_bbox_from_step, estimate_volume_from_bbox, get_material_density
from src.runtime.export_bundler import create_bundle

# === 报价引擎 (纯数学, 零AI) ===
MAT_COEFS = {
    "45钢": 1.0, "45#": 1.0, "q235": 0.9,
    "6061": 1.3, "al6061": 1.3, "7075": 1.6,
    "304": 1.5, "sus304": 1.5, "316l": 1.8, "sus316": 1.8,
    "tc4": 5.4, "钛合金": 5.4, "h59": 2.0, "黄铜": 2.0,
}
SURF_COEFS = {"无": 1.0, "发黑": 1.2, "阳极氧化": 1.6, "镀锌": 1.3, "镀铬": 1.8, "镀镍": 1.6, "磷化": 1.2, "喷漆": 1.1}
SURF_VALID = {
    ("6061", "阳极氧化"): True, ("al6061", "阳极氧化"): True,
    ("45钢", "发黑"): True, ("45#", "发黑"): True,
    ("45钢", "镀锌"): True, ("45#", "镀锌"): True,
    ("45钢", "镀铬"): True, ("45#", "镀铬"): True,
    ("45钢", "磷化"): True, ("45#", "磷化"): True,
    ("304", "发黑"): True, ("sus304", "发黑"): True,
    ("304", "镀镍"): True, ("sus304", "镀镍"): True,
    ("316l", "发黑"): True,
    ("tc4", "阳极氧化"): True, ("钛合金", "阳极氧化"): True,
    ("tc4", "镀镍"): True, ("钛合金", "镀镍"): True,
    ("q235", "镀锌"): True, ("q235", "喷漆"): True,
}

def calc_quote(material="6061", surface="无", quantity=10, weight_kg=0.5):
    mat_key = material.lower()
    mat_coef = MAT_COEFS.get(mat_key, MAT_COEFS.get(material, 1.3))
    surf_coef = SURF_COEFS.get(surface, 1.0)
    valid = SURF_VALID.get((material.lower(), surface), SURF_VALID.get((material, surface), True))
    conflicts = []
    if not valid:
        conflicts.append({"severity": "error", "message": f"{material}+{surface} 工艺不支持"})
    if quantity <= 0: quantity = 10
    if weight_kg <= 0: weight_kg = 0.5
    base_price = 15.0 + 60.0 * weight_kg * mat_coef
    unit_price = base_price * surf_coef
    volume_discount = 1.0
    if quantity >= 100: volume_discount = 0.7
    elif quantity >= 50: volume_discount = 0.8
    elif quantity >= 20: volume_discount = 0.9
    total = unit_price * quantity * volume_discount
    profit = total * 0.25
    final = total + profit
    return {
        "material": material, "surface": surface, "quantity": quantity,
        "weight_kg": round(weight_kg, 3), "unit_price": round(unit_price, 2),
        "total_price": round(total, 2), "profit": round(profit, 2),
        "final_price": round(final, 2),
        "volume_discount": volume_discount,
        "valid": len(conflicts) == 0, "conflicts": conflicts, "warnings": [],
        "disclaimer": "以上为AI估算，实际加工前请人工确认。"
    }

# === 新手引导机器人 (规则引擎, 无需AI) ===
PART_KEYWORDS = {
    "法兰": "flange", "法兰盖": "flange", "闷盖": "flange",
    "轴套": "sleeve", "衬套": "sleeve",
    "轴": "shaft", "光轴": "shaft",
    "板": "plate", "平板": "plate",
    "箱体": "box", "盒子": "box", "方块": "block",
    "支架": "bracket", "支板": "bracket",
}

def extract_params(msg):
    p = {"material": "6061", "surface": "无", "quantity": 10, "weight_kg": 0.5}
    msg_lower = msg.lower()
    for mat in ["45钢", "6061", "304", "316l", "q235", "tc4", "钛合金"]:
        if mat in msg or mat in msg_lower:
            p["material"] = mat
            break
    for s in ["阳极氧化", "发黑", "镀锌", "镀铬", "镀镍", "磷化", "喷漆"]:
        if s in msg:
            p["surface"] = s
            break
    m = re.search(r'(\d+)\s*件', msg)
    if m: p["quantity"] = int(m.group(1))
    m = re.search(r'(\d+\.?\d*)\s*kg', msg_lower)
    if m: p["weight_kg"] = float(m.group(1))
    return p

def bot_reply(message):
    msg = message.strip()
    ml = msg.lower()
    if any(k in msg for k in ["你好", "hi", "hello", "在吗"]):
        return {"reply": "我是Union由你。试试：\n- 画一个法兰 外径100内径50厚20\n- 6061法兰 50件 阳极氧化 报价\n- 帮助", "type": "greeting"}
    if any(k in msg for k in ["帮助", "help", "怎么用", "功能"]):
        return {"reply": (
            "**画图**: 画一个法兰 外径100内径50厚20\n"
            "**报价**: 6061法兰 50件 阳极氧化 多少钱\n"
            "**上传**: 拖拽STEP/STL到上传区\n"
            "**导出**: 一键打包ZIP\n"
            "装Ollama才有: AI对话/专家会议/工艺建议"
        ), "type": "help"}
    is_draw = any(k in msg for k in ["画", "生成", "创建", "建模"]) and any(pt in msg for pt in PART_KEYWORDS)
    if is_draw:
        part_type = "flange"
        for cn, en in PART_KEYWORDS.items():
            if cn in msg: part_type = en; break
        params = {"od": 100, "id": 50, "thickness": 20}
        od_m = re.search(r'外径\s*(\d+)', msg) or re.search(r'od\s*(\d+)', ml)
        id_m = re.search(r'内径\s*(\d+)', msg) or re.search(r'id\s*(\d+)', ml)
        th_m = re.search(r'厚\s*(\d+)', msg) or re.search(r'厚度\s*(\d+)', msg)
        len_m = re.search(r'长\s*(\d+)', msg) or re.search(r'长度\s*(\d+)', msg)
        w_m = re.search(r'宽\s*(\d+)', msg) or re.search(r'w\s*(\d+)', ml)
        h_m = re.search(r'高\s*(\d+)', msg) or re.search(r'h\s*(\d+)', ml)
        if od_m: params["od"] = int(od_m.group(1))
        if id_m: params["id"] = int(id_m.group(1))
        if th_m: params["thickness"] = int(th_m.group(1))
        if len_m: params["length"] = int(len_m.group(1))
        if w_m: params["w"] = int(w_m.group(1))
        if h_m: params["h"] = int(h_m.group(1))
        gen = generate_part(part_type, params)
        if "error" in gen:
            return {"reply": gen["error"]}
        bbox = gen.get("bounding_box_mm", [100, 100, 20])
        lines = [
            "## " + part_type + " 已生成",
            f"尺寸: {bbox[0]}x{bbox[1]}x{bbox[2]} mm",
            f"体积: {gen.get('volume_cm3', '-')} cm3",
            f"预估重量(6061): {gen.get('estimated_weight_g', '-')} g",
            "3D预览: 右侧模型区已加载",
            "继续: 说出材料和数量即可报价",
        ]
        return {"reply": "\n".join(lines), "type": "step", "stl_url": gen.get("stl_url"), "step_file": gen.get("step_file")}
    is_quote = any(k in ml for k in ["报价", "价格", "多少钱", "成本"])
    if is_quote:
        params = extract_params(msg)
        q = calc_quote(**params)
        lines = [
            "## 报价明细",
            f"材料: {q['material']} | 表面: {q['surface']} | 数量: {q['quantity']}件 | 重量: {q['weight_kg']}kg",
            "",
            f"| 项目 | 金额 |",
            f"|------|------|",
            f"| 单价 | {q['unit_price']:.2f} |",
            f"| 小计 | {q['total_price']:.2f} |",
            f"| 利润 | {q['profit']:.2f} |",
            f"| 总价 | {q['final_price']:.2f} |",
            "",
            "以上为AI估算，实际加工前请人工确认。",
        ]
        if not q["valid"]:
            for c in q["conflicts"]:
                lines.append("! " + c['message'])
        return {"reply": "\n".join(lines), "type": "quote"}
    return {"reply": (
        "我是离线模式，支持: 画图/报价/上传/打包\n\n"
        "试试:\n"
        "- 画法兰 - 画一个法兰 外径100内径50厚20\n"
        "- 报价 - 6061法兰 50件 阳极氧化 多少钱\n"
        "- 帮助 - 查看全部功能\n\n"
        "装Ollama + qwen2.5:3b 解锁AI专家会议"
    ), "type": "unknown"}

# === 冲突检测 (纯规则) ===
CONFLICT_RULES = [
    ("304", "阳极氧化", False, "304不锈钢自然钝化，不进行阳极氧化"),
    ("316l", "阳极氧化", False, "316L不锈钢不进行阳极氧化"),
    ("tc4", "镀锌", False, "钛合金不进行镀锌处理"),
    ("6061", "镀锌", False, "铝合金不适合镀锌"),
    ("q235", "阳极氧化", False, "碳钢不进行阳极氧化"),
    ("6061", "电镀", True, "铝合金可电镀但附着力需预镀"),
    ("304", "电镀", True, "304可电镀但无必要"),
    ("45钢", "阳极氧化", False, "碳钢不进行阳极氧化"),
]
def check_conflict(material, surface):
    conflicts = []
    for m, s, mild, desc in CONFLICT_RULES:
        if (material.lower() == m.lower()) and \
           (surface in s or s in surface):
            conflicts.append({"severity": "warn" if mild else "error", "rule": m+":"+s, "message": desc})
    return {"valid": len([c for c in conflicts if c["severity"]=="error"])==0, "conflicts": conflicts}

def detect_ollama():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        return {"available": True, "models": [m["name"] for m in data.get("models", [])]}
    except:
        return {"available": False, "models": []}

import urllib.request

app = FastAPI(title="Union由你 Lite", version="11.0.4-lite")

with open(PROJECT_ROOT / "app" / "static" / "index_lite.html", encoding="utf-8") as f:
    HTML_PAGE = f.read()

@app.get("/", response_class=HTMLResponse)
async def index(): return HTMLResponse(content=HTML_PAGE)

@app.get("/api/status")
async def status():
    return JSONResponse(content={
        "mode": "lite", "version": "11.0.4-lite",
        "parts": list(PART_GENERATORS.keys()),
        "materials": list(MAT_COEFS.keys()),
        "surfaces": list(SURF_COEFS.keys()),
        "ollama": detect_ollama(),
    })

@app.get("/api/version")
async def version(): return JSONResponse(content={"version": "11.0.4", "codename": "工业炼金术师(Lite)", "mode": "lite"})

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    msg = body.get("message", "").strip()
    if not msg: return JSONResponse(content={"reply": "请输入需求。"})
    result = bot_reply(msg)
    if result.get("type") not in ("greeting", "help"):
        result["disclaimer"] = "以上为AI估算，实际加工前请人工确认。"
        result["shadow_mode"] = True
    return JSONResponse(content=result)

@app.post("/api/generate-step")
async def generate_step_api(request: Request):
    try: params = await request.json()
    except: return JSONResponse(content={"error": "需要JSON参数"}, status_code=400)
    result = generate_part(params.get("part_type", "flange"), params)
    if "error" in result: return JSONResponse(content=result, status_code=400)
    return JSONResponse(content=result)

@app.get("/api/preview/{filename}")
async def preview_stl(filename: str):
    stl_path = PROJECT_ROOT / "data" / "step" / filename
    if not stl_path.exists():
        return JSONResponse(content={"error": "文件不存在"}, status_code=404)
    return FileResponse(stl_path, media_type="application/octet-stream")

@app.post("/api/upload-step")
async def upload_step_quote(file: UploadFile = File(...), material: str = Form("6061"),
                            quantity: int = Form(10), surface: str = Form("无")):
    upload_dir = PROJECT_ROOT / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    bbox = extract_bbox_from_step(str(file_path))
    if not bbox or "error" in bbox:
        return JSONResponse(content={"error": "STEP解析失败", "detail": bbox}, status_code=400)
    volume_mm3 = estimate_volume_from_bbox(bbox)
    volume_cm3 = volume_mm3 / 1000
    density = get_material_density(material)
    weight_kg = (volume_cm3 * density) / 1000
    q = calc_quote(material=material, surface=surface, quantity=quantity, weight_kg=weight_kg)
    return JSONResponse(content={
        "file_name": file.filename,
        "bounding_box": {"x": round(bbox["dim_x"],1), "y": round(bbox["dim_y"],1), "z": round(bbox["dim_z"],1)},
        "volume_mm3": round(volume_mm3,0), "volume_cm3": round(volume_cm3,2),
        "estimated_weight_kg": round(weight_kg,3),
        "quote": q, "disclaimer": "AI估算，仅供参考",
    })

@app.post("/api/export")
async def export_bundle(request: Request):
    try: params = await request.json()
    except: return JSONResponse(content={"error": "需要JSON参数"}, status_code=400)
    task_id = params.get("task_id", uuid.uuid4().hex[:8])
    files = params.get("files", [])
    files_exist = [f for f in files if os.path.exists(str(PROJECT_ROOT / "data" / f.get("path", ""))) or os.path.exists(f.get("path", ""))]
    result = create_bundle(task_id, files_exist, params.get("quote"), {"task_id": task_id, "created": datetime.now().isoformat()})
    return JSONResponse(content=result)

@app.get("/api/download/{filename}")
async def download_zip(filename: str):
    zip_path = PROJECT_ROOT / "data" / "exports" / filename
    if not zip_path.exists():
        return JSONResponse(content={"error": "文件不存在"}, status_code=404)
    return FileResponse(zip_path, media_type="application/zip", filename=filename)

@app.get("/api/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content="""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>仪表盘</title>
<style>body{font-family:Arial;background:#0f172a;color:#e2e8f0;padding:24px}
h1{color:#38bdf8;font-size:20px}.v{font-size:24px;color:#38bdf8;font-weight:bold}
.c{background:#1e293b;border-radius:12px;padding:16px;margin:8px 0;border:1px solid #334155}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.l{font-size:11px;color:#94a3b8}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
th{color:#94a3b8;font-size:11px;text-align:left;padding:6px 0;border-bottom:1px solid #334155}
td{padding:6px 0;border-bottom:1px solid #1e293b}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;margin-right:8px;font-size:10px}
.green{background:#166534;color:#86efac}.red{background:#7f1d1d;color:#fca5a5}
</style></head><body>
<h1>CNC AI Brain Lite v11.0.4</h1>
<div class="g">
<div class="c"><div class="l">模式</div><div class="v">Lite</div></div>
<div class="c"><div class="l">报价</div><div class="v">纯规则</div></div>
<div class="c"><div class="l">STEP</div><div class="v">trimesh</div></div>
<div class="c"><div class="l">3D</div><div class="v">Three.js</div></div>
</div>
<h2 style="margin-top:20px">报价梯度</h2>
<table><tr><th>材料</th><th>50件</th><th>倍率</th></tr>
<script>
(function(){let d=[["45钢","5891","基准"],["6061","7656","1.3x"],["304","9063","1.5x"],["316L","10875","1.8x"],["TC4","31719","5.4x"]];
document.write(d.map(r=>"<tr><td>"+r[0]+"</td><td>"+r[1]+"</td><td>"+r[2]+"</td></tr>").join(""));})();
</script></table>
<h2>冲突规则</h2>
<div><span class="tag green">6061+阳极氧化</span></div>
<div><span class="tag green">45钢+发黑</span></div>
<div><span class="tag red" style="">304+阳极氧化</span></div>
<div><span class="tag tag-" style="">TC4+镀锌</span></div>
</body></html>""")

@app.get("/api/health")
async def health():
    return JSONResponse(content={
        "status": "healthy", "mode": "lite", "version": "11.0.4-lite",
        "ollama_available": detect_ollama()["available"],
    })

@app.get("/api/demo")
async def demo():
    scenes = []
    try:
        r = generate_part("flange", {"od": 100, "id": 50, "thickness": 20})
        scenes.append({"scene": "STEP生成", "status": "ok" if "error" not in r else "error", "preview": r.get("stl_url", "")})
    except Exception as e:
        scenes.append({"scene": "STEP生成", "status": "error", "error": str(e)})
    try:
        r = calc_quote("6061", "阳极氧化", 50)
        scenes.append({"scene": "报价", "status": "ok", "price": r.get("final_price", 0)})
    except Exception as e:
        scenes.append({"scene": "报价", "status": "error", "error": str(e)})
    try:
        r = check_conflict("304", "阳极氧化")
        scenes.append({"scene": "冲突检测", "status": "blocked" if not r["valid"] else "ok"})
    except Exception as e:
        scenes.append({"scene": "冲突检测", "status": "error", "error": str(e)})
    return JSONResponse(content={"title": "v11.0.4 Lite 演示", "scenes": scenes})

if __name__ == "__main__":
    print(" Union由你 Lite v11.0.4 - 离线工业炼金术师")
    print(" 零AI依赖 | 画图/报价/预览/打包")
    print(" http://localhost:7861")
    uvicorn.run(app, host="0.0.0.0", port=7861, log_level="warning")
