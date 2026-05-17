#!/usr/bin/env python3
"""Export Bundler — STEP + 报价 + 图纸 → ZIP
作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统"""
import os, json, zipfile, io
from pathlib import Path
from datetime import datetime

EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

def create_bundle(task_id: str, files: list, quote_data: dict = None, 
                  metadata: dict = None) -> dict:
    """创建交付ZIP包
    files: [{"path": "/abs/path", "name": "display_name.step"}, ...]
    quote_data: 报价JSON
    metadata: 任务元数据
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 加文件
        for f in files:
            if os.path.exists(f["path"]):
                zf.write(f["path"], f["name"])
        
        # 加报价Excel (CSV格式)
        if quote_data:
            csv_lines = [
                "项目,值",
                f"材料,{quote_data.get('material', '-')}",
                f"数量,{quote_data.get('quantity', '-')}",
                f"表面处理,{quote_data.get('surface_treatment', '无')}",
                f"单件重量(kg),{quote_data.get('weight_kg', '-')}",
                f"单件价格,{quote_data.get('unit_price', '-')}",
                f"总价,{quote_data.get('total_price', '-')}",
                f"生成时间,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
            zf.writestr("报价明细.csv", "\n".join(csv_lines))
        
        # 加元数据
        if metadata:
            zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        
        # 加免责声明
        disclaimer = (
            "此报价由 CNC AI 工艺大脑 生成，仅供参考。\n"
            "实际加工前请人工确认所有参数。\n"
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "作者: timo.cao | 生成: 大帅教练系统\n"
        )
        zf.writestr("README.txt", disclaimer)
    
    # 保存
    zip_name = f"bundle_{task_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = EXPORT_DIR / zip_name
    zip_path.write_bytes(buf.getvalue())
    
    return {
        "zip_file": str(zip_path),
        "zip_url": f"/api/download/{zip_name}",
        "size_kb": round(len(buf.getvalue()) / 1024, 1),
        "files_count": len(files) + (1 if quote_data else 0),
    }
