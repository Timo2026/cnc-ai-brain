"""
模型注册表 — 统一管理本地Ollama + 云端API模型。
零硬编码，自动检测+手动配置双通道。
作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统
"""
import json, os
from pathlib import Path
from typing import Dict, Any, List, Optional


class ModelRegistry:
    """统一模型注册表。合并Ollama自动检测 + 云端配置，按质量排序。"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).resolve().parent.parent.parent / "config" / "models.json"
        self._config = self._load_config()
        self._all_models = []

    def _load_config(self) -> dict:
        """加载模型配置文件。文件不存在则返回默认空配置。"""
        if self.config_path and self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                return json.load(f)
        return {"cloud": [], "preference": "auto", "selection_rules": {}}

    def detect_ollama_models(self) -> List[Dict[str, Any]]:
        """自动检测本机Ollama已安装模型。"""
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            models = []
            for m in data.get("models", []):
                name = m.get("name", "unknown")
                size_gb = round(m.get("size", 0) / (1024**3), 2)
                param_size = m.get("details", {}).get("parameter_size", "0B")
                param_count = self._parse_param(param_size)
                models.append({
                    "name": name, "size_gb": size_gb, "param_size": param_size,
                    "param_count": param_count, "source": "ollama",
                    "quality_score": self._score_local(name, param_count),
                    "provider": "ollama",
                })
            return models
        except Exception:
            return []

    def load_cloud_models(self) -> List[Dict[str, Any]]:
        """从配置文件加载云端模型列表。"""
        models = []
        for cfg in self._config.get("cloud", []):
            name = cfg.get("name", "unknown")
            models.append({
                "name": name,
                "provider": cfg.get("provider", "openai"),
                "api_key": cfg.get("api_key", ""),
                "api_url": cfg.get("api_url", ""),
                "model_id": cfg.get("model_id", name),
                "quality_score": cfg.get("quality_score", 50),
                "param_count": cfg.get("param_count", 10),
                "source": "cloud",
                "description": cfg.get("description", ""),
            })
        return models

    def get_all_ranked(self, preference: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有可用模型，按质量排序。"""
        pref = preference or self._config.get("preference", "auto")
        ollama_models = self.detect_ollama_models()
        cloud_models = self.load_cloud_models()

        # 过滤：云端模型必须已配置API key
        valid_cloud = [m for m in cloud_models if m.get("api_key") and m.get("api_key") != "sk-your-key-here"]

        if pref == "local":
            all_models = ollama_models + valid_cloud
        elif pref == "cloud":
            all_models = valid_cloud + ollama_models
        else:
            all_models = ollama_models + valid_cloud

        all_models.sort(key=lambda m: m.get("quality_score", 0), reverse=True)
        return all_models

    def select_best(self, min_quality: int = 0, task: str = "chat") -> Optional[Dict[str, Any]]:
        """按任务类型选择最佳模型。"""
        rules = self._config.get("selection_rules", {}).get(task, {})
        pref = rules.get("prefer", self._config.get("preference", "auto"))
        min_q = rules.get("min_quality", min_quality)

        all_models = self.get_all_ranked(pref)
        for m in all_models:
            if m.get("quality_score", 0) >= min_q:
                return m
        return all_models[0] if all_models else None

    @staticmethod
    def _parse_param(param_str: str) -> float:
        """解析 '1.5B' → 1.5, '7B' → 7.0"""
        try:
            return float(param_str.upper().replace("B", "").strip())
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _score_local(name: str, param_count: float) -> float:
        """本地模型质量评分（~100满分）。"""
        name_lower = name.lower()
        score = param_count * 8
        if any(k in name_lower for k in ("qwen", "glm", "chatglm", "baichuan", "yi", "deepseek")):
            score += 30
        if any(k in name_lower for k in ("llama", "gemma")):
            score -= 10
        if "granite" in name_lower:
            score -= 20
        return max(score, 0)

    def get_report(self) -> str:
        """状态报告JSON。"""
        all_m = self.get_all_ranked()
        best = self.select_best()
        return json.dumps({
            "total_models": len(all_m),
            "ollama_count": len([m for m in all_m if m["source"] == "ollama"]),
            "cloud_count": len([m for m in all_m if m["source"] == "cloud"]),
            "best_model": best,
            "all_models": [{"name": m["name"], "source": m["source"], "score": m["quality_score"]} for m in all_m[:10]],
        }, ensure_ascii=False, indent=2)
