# Union·由你 CNC AI 工艺大脑 v11.0.4 — Windows 部署

## 两种模式

### 模式 A：纯本地（Ollama，推荐）

1. 装 Ollama: https://ollama.com/download/windows
2. 拉模型: `ollama pull qwen2.5:3b`
3. 双击 `install_windows.bat`

系统自动检测Ollama模型，自动选最优。

### 模式 B：云端API（DeepSeek/GLM/通义）

编辑 `config\models.json`，填入你的API key：

```json
{
  "cloud": [
    {
      "name": "deepseek-chat",
      "provider": "openai",
      "api_key": "sk-你的key",
      "api_url": "https://api.deepseek.com/v1",
      "model_id": "deepseek-chat",
      "quality_score": 95
    }
  ]
}
```

支持所有 OpenAI 兼容接口：DeepSeek、智谱GLM、通义千问、Moonshot、Claude(OpenAI兼容版)等。

双击 `install_windows.bat`，系统自动选最高质量的可用模型。

### 模式 C：混合

本地跑专家会议（低延迟），云端跑CEO决策（高质量）。

全自动，无需手动切换。

## 系统要求

- Windows 10/11 (x64)
- Python 3.10+
- 模式A需要: Ollama + 约2GB下载

## 启动后

| 地址 | 功能 |
|------|------|
| http://localhost:7861 | 主界面 — 画图/报价/3D预览 |
| http://localhost:7861/api/models | 模型列表 — 查看可用模型 |
| http://localhost:7861/api/health | 健康检查 |
| http://localhost:7861/api/dashboard | 仪表盘 |

## 模型配置说明

系统启动时会：
1. 自动扫描本机Ollama所有模型 → 质量评分排序
2. 检查 `config/models.json` 中配置的云端API
3. 按质量分从高到低选最优模型

**不需要手动指定模型。不需要硬编码。**

作者: timo.cao | 邮箱: miscdd@163.com | 生成: 大帅教练系统 (dashuai coach)
