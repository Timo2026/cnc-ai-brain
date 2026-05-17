# Union·由你 — CNC AI 工艺大脑 v11.0.2

> 全离线工业AI系统。不联网、不调云API、数据不出车间。

[![Version](https://img.shields.io/badge/version-11.0.2-blue)](https://github.com/Timo2026/cnc-ai-brain)
[![Python](https://img.shields.io/badge/python-3.10%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)
[![Status](https://img.shields.io/badge/status-demo--ready-brightgreen)]()

## 一句话

输入材料和数量，1秒算报价，70秒做接单决策。全本地运行，零云依赖。

## 30秒看懂

```
┌─────────────────────────────────────────────────┐
│  用户输入: "6061法兰 50件 阳极氧化 报价"         │
│       ↓                                         │
│  报价路径(<1s) → rule-based引擎 → ¥7,656         │
│  冲突路径(<1s) → 10条硬规则   → 304+阳极氧化? 阻断│
│  专家路径(~70s)→ 3专家串行+CEO → 钛合金IT5? 否决 │
│       ↓                                         │
│  审计哈希链 (防篡改)                              │
└─────────────────────────────────────────────────┘
```

## 核心能力

| 能力 | 说明 | 性能 |
|------|------|------|
| 智能报价 | 5种材料梯度, 纯Python规则引擎 | <1s |
| 工艺冲突 | 10条硬规则(材料-表面-公差) | <1s |
| 专家会议 | 3专家串行+一票否决+CEO裁决 | ~70s |
| 审计防篡改 | SQLite哈希链 | 零开销 |
| 零硬编码 | 自适应硬件/模型/Skill | 启动时 |

## 报价梯度

| 材料 | 10件 | 50件 | 单价 | 倍率 |
|------|------|------|------|------|
| 45钢 | ¥1,178 | ¥5,891 | ¥117.81 | 基准 |
| 6061铝合金 | ¥1,541 | ¥7,656 | ¥154.06 | 1.3x |
| 304不锈钢 | ¥1,813 | ¥9,063 | ¥181.25 | 1.5x |
| 316L不锈钢 | ¥2,175 | ¥10,875 | ¥217.50 | 1.8x |
| 钛合金TC4 | ¥6,344 | ¥31,719 | ¥634.38 | 5.4x |

## 快速开始

### Linux (推荐)

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 拉取模型
ollama pull qwen2.5:3b

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
python3 app/main.py
# → http://localhost:7861
```

### Windows 一键安装

```cmd
# 下载并解压后, 双击运行:
install_windows.bat
# 自动安装 Ollama → 拉模型 → 装依赖 → 启动服务
```

### Docker

```bash
docker-compose up -d
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 对话前端 |
| `/api/chat` | POST | 对话API |
| `/api/health` | GET | 工厂IT自检 |
| `/api/demo` | GET | 5场景演示 |
| `/api/dashboard` | GET | 实时仪表盘 |
| `/api/conflict-check` | POST | 工艺冲突 |
| `/api/audit` | GET | 审计查询 |

## 项目结构

```
cnc-ai-brain/
├── app/main.py              # FastAPI 入口 + HTML前端
├── src/
│   ├── core/                # 环境探测 + 模型自选 + Skill加载
│   ├── ai_engine/           # Ollama 推理引擎
│   ├── neuro_core/          # 专家会议引擎 + 冲突检测 + Schema校验
│   ├── runtime/             # 报价适配器 + 历史查询 + 事件总线
│   └── safety/              # 审计日志 (哈希链)
├── config/
│   ├── experts/             # 5位专家 YAML (含JSON Schema)
│   └── skills/              # 3项技能 YAML
├── deploy/                  # systemd + 演示部署 + Windows脚本
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Ollama+App 一键部署
└── union_by_ni.spec         # PyInstaller 打包
```

## 部署方式

| 方式 | 适用 | 命令 |
|------|------|------|
| 直接运行 | 开发/演示 | `python3 app/main.py` |
| systemd | Linux服务器 | `sudo systemctl enable cnc-brain` |
| Docker | 容器化 | `docker-compose up -d` |
| EXE | Windows工控机 | PyInstaller 打包 |

## 专家阵容

| 专家 | 职责 | 否决权 |
|------|------|--------|
| CFO | 利润/现金流/回款 | ✅ 一票否决 |
| BI分析师 | 客户历史/市场趋势 | - |
| 战略官 | 产能/长期价值 | - |
| 工艺总监 | 公差/设备/刀具 | - |
| CEO | 最终裁决 | ✅ 可覆写否决 |

## 演示场景

```
S1: 6061法兰 50件 阳极氧化 → ¥7,656 (常规报价)
S2: 钛合金TC4 10件 → ¥6,344 (高价材料梯度)
S3: 304法兰 阳极氧化 → ❌ 工艺冲突阻断
S4: 304法兰 钝化 → ¥1,813 (冲突修复后报价)
S5: 钛合金IT5 5万预算 → REJECTED (专家否决)
```

## 版本

| 版本 | 日期 | 变更 |
|------|------|------|
| v11.0.0 | 2026-05-17 | P0清零·报价正确·可演示 |
| v11.0.1 | 2026-05-17 | Schema校验器 + 重试 |
| v11.0.2 | 2026-05-17 | 演示就绪·仪表盘·systemd |

## 作者

- 作者: timo.cao
- 邮箱: miscdd@163.com
- 生成: 大帅教练系统 (dashuai coach)
