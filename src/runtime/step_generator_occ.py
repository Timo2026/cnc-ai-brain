"""STEP Generator OCC — 使用 pythonocc-core 生成 B-Rep 精确 STEP
支持: flange, sleeve, shaft, plate, box, bracket
用OCC生成时STEP文件是精确几何（不是三角网格），CAM软件直接出刀路。
作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统"""
import os, math, json, tempfile
from pathlib import Path

# OCC 导入 — 容错处理
_OCC_AVAILABLE = False
try:
    from OCC.Core.BRepPrimAPI import (BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox,
                                       BRepPrimAPI_MakePrism)
    from OCC.Core.gp import gp_Ax2, gp_Pnt, gp_Dir, gp_Circ, gp_Pln, gp_Vec
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCC.Core.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
                                          BRepBuilderAPI_MakeFace)
    from OCC.Core.Geom import Geom_CylindricalSurface
    from OCC.Core.TopoDS import TopoDS_Shape
    from OCC.Core.gp import gp_OX, gp_OY, gp_OZ
    _OCC_AVAILABLE = True
except ImportError:
    pass

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "step"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_OCC_GENERATORS = {}


def occ_available() -> bool:
    """检查OCC是否可用。"""
    return _OCC_AVAILABLE


def register_occ(name):
    """注册一个OCC零件生成器。"""
    def dec(fn):
        _OCC_GENERATORS[name] = fn
        return fn
    return dec


def _make_step(shape: TopoDS_Shape, filename: str) -> str:
    """将OCC Shape导出为STEP文件。"""
    filepath = str(OUTPUT_DIR / filename)
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(filepath)
    return filepath


def _bbox(shape: TopoDS_Shape) -> tuple:
    """计算OCC Shape的包围盒."""
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    b = Bnd_Box()
    brepbndlib.Add(shape, b)
    xmin, ymin, zmin, xmax, ymax, zmax = b.Get()
    return (round(xmax - xmin, 1), round(ymax - ymin, 1), round(zmax - zmin, 1))


def _result(shape: TopoDS_Shape, part_type: str, params: dict) -> dict:
    """统一结果格式 — 与 trimesh 生成器兼容。"""
    step_name = f"{part_type}_occ_{abs(hash(str(params))) % 10000}.step"
    step_path = _make_step(shape, step_name)
    bbox = _bbox(shape)
    # OCC STEP是从B-Rep精确几何导出的，文件大小远小于trimesh三角网格
    # 对同一零件，OCC: ~9KB, trimesh: ~280KB
    file_size = os.path.getsize(step_path)
    return {
        "engine": "OCC",
        "step_file": step_path,
        "file_size_bytes": file_size,
        "bounding_box_mm": list(bbox),
        "volume_mm3": round(bbox[0] * bbox[1] * bbox[2], 0),
        "params": params,
        "note": "B-Rep精确几何 — CAM可直接加工"
    }


# ══════════════════════════════════════════════════
# 零件生成器
# ══════════════════════════════════════════════════

@register_occ("flange")
def make_flange(params: dict) -> dict:
    """法兰 — OCC精确B-Rep"""
    od = params.get("od", 100)
    id_ = params.get("id", 50)
    thickness = params.get("thickness", 20)
    outer = BRepPrimAPI_MakeCylinder(od / 2.0, thickness).Shape()
    inner = BRepPrimAPI_MakeCylinder(id_ / 2.0, thickness).Shape()
    shape = BRepAlgoAPI_Cut(outer, inner).Shape()
    return _result(shape, "flange", params)


@register_occ("sleeve")
def make_sleeve(params: dict) -> dict:
    """轴套 — OCC精确B-Rep"""
    od = params.get("od", 60)
    id_ = params.get("id", 30)
    length = params.get("length", 100)
    outer = BRepPrimAPI_MakeCylinder(od / 2.0, length).Shape()
    inner = BRepPrimAPI_MakeCylinder(id_ / 2.0, length).Shape()
    shape = BRepAlgoAPI_Cut(outer, inner).Shape()
    return _result(shape, "sleeve", params)


@register_occ("shaft")
def make_shaft(params: dict) -> dict:
    """轴 — OCC精确B-Rep"""
    diameter = params.get("od", 30)
    length = params.get("length", 200)
    shape = BRepPrimAPI_MakeCylinder(diameter / 2.0, length).Shape()
    return _result(shape, "shaft", params)


@register_occ("plate")
def make_plate(params: dict) -> dict:
    """平板 — OCC精确B-Rep"""
    w = params.get("w", params.get("width", 150))
    h = params.get("h", params.get("height", 100))
    t = params.get("thickness", 10)
    shape = BRepPrimAPI_MakeBox(w, h, t).Shape()
    return _result(shape, "plate", params)


@register_occ("box")
def make_box(params: dict) -> dict:
    """箱体 — OCC精确B-Rep"""
    w = params.get("w", params.get("width", 200))
    h = params.get("h", params.get("height", 100))
    d = params.get("d", params.get("depth", 150))
    thickness = params.get("thickness", 5)
    outer = BRepPrimAPI_MakeBox(w, h, d).Shape()
    inner = BRepPrimAPI_MakeBox(w - 2*thickness, h - 2*thickness, d - 2*thickness).Shape()
    inner_loc = gp_Pnt(thickness, thickness, thickness)
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.gp import gp_Trsf
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(thickness, thickness, thickness))
    inner_moved = BRepBuilderAPI_Transform(inner, tr).Shape()
    shape = BRepAlgoAPI_Cut(outer, inner_moved).Shape()
    return _result(shape, "box", params)


@register_occ("bracket")
def make_bracket(params: dict) -> dict:
    """支架 — OCC精确B-Rep (近似: 平板+底座)"""
    w = params.get("w", 80)
    h = params.get("h", 120)
    t = params.get("thickness", 10)
    base = BRepPrimAPI_MakeBox(w, 30, t).Shape()
    wall = BRepPrimAPI_MakeBox(t, h, w).Shape()
    from OCC.Core.gp import gp_Trsf
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(0, 30, 0))
    wall_moved = BRepBuilderAPI_Transform(wall, tr).Shape()
    shape = BRepAlgoAPI_Fuse(base, wall_moved).Shape()
    return _result(shape, "bracket", params)


def generate_part_occ(part_type: str, params: dict) -> dict:
    """OCC统一入口 — 与trimesh generate_part相同签名。"""
    gen = _OCC_GENERATORS.get(part_type)
    if not gen:
        return {"error": f"OCC不支持: {part_type}", "available": list(_OCC_GENERATORS.keys())}
    try:
        return gen(params)
    except Exception as e:
        return {"error": f"OCC生成失败: {e}"}


def get_occ_parts() -> list:
    """可用OCC零件类型列表。"""
    return list(_OCC_GENERATORS.keys())


def occ_status() -> dict:
    """OCC引擎状态。"""
    return {
        "available": _OCC_AVAILABLE,
        "parts": get_occ_parts(),
        "engine": "OCC (B-Rep精确几何)"
    }
