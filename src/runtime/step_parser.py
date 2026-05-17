#!/usr/bin/env python3
"""STEP Parser — 从STEP文件提取包围盒(CARTESIAN_POINT解析)
复用的 batch_quote.py 核心逻辑, 轻量化版本
作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统"""
import re, os
from pathlib import Path

def extract_bbox_from_step(filepath: str) -> dict | None:
    """从STEP文件提取包围盒 — 解析CARTESIAN_POINT嵌套括号"""
    try:
        with open(filepath, 'r', errors='ignore') as f:
            content = f.read()
        
        points = []
        # 模式1: CARTESIAN_POINT('label', (x, y, z))
        pattern1 = r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*\)"
        for m in re.finditer(pattern1, content):
            points.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
        
        if not points:
            # 模式2: #N = CARTESIAN_POINT(...(x, y, z))
            pattern2 = r"#\d+\s*=\s*CARTESIAN_POINT\s*\([^)]*\(\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*\)"
            for m in re.finditer(pattern2, content):
                points.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
        
        if not points:
            return None
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        zs = [p[2] for p in points]
        
        bbox = {
            "x_min": round(min(xs), 2),
            "x_max": round(max(xs), 2),
            "y_min": round(min(ys), 2),
            "y_max": round(max(ys), 2),
            "z_min": round(min(zs), 2),
            "z_max": round(max(zs), 2),
            "dim_x": round(max(xs) - min(xs), 2),
            "dim_y": round(max(ys) - min(ys), 2),
            "dim_z": round(max(zs) - min(zs), 2),
            "total_points": len(points),
        }
        return bbox
    except Exception as e:
        return {"error": str(e)}

def estimate_volume_from_bbox(bbox: dict, solid_ratio: float = 0.30) -> float:
    """包围盒 → 估计体积(mm³)"""
    return bbox["dim_x"] * bbox["dim_y"] * bbox["dim_z"] * solid_ratio

# 材料密度 (g/cm³)
DENSITY = {
    "AL6061": 2.70, "6061": 2.70, "AL7075": 2.81,
    "SUS304": 7.93, "304": 7.93, "SUS316": 7.98, "316L": 7.98,
    "45钢": 7.85, "45#": 7.85, "Q235": 7.85,
    "TC4": 4.43, "钛合金": 4.43,
    "H59": 8.50, "黄铜": 8.50,
}

def get_material_density(material: str) -> float:
    return DENSITY.get(material.upper(), DENSITY.get(material, 7.85))

# 表面处理费 (¥/cm²)
SURFACE_COST = {
    "阳极氧化": 0.05, "发黑": 0.02, "镀锌": 0.03,
    "电镀": 0.08, "钝化": 0.03, "喷漆": 0.06,
    "无": 0, "": 0, None: 0,
}
