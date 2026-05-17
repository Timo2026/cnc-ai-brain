# 🦞 Union·由你 — CNC AI 工艺大脑

**v11.0-AutoAdapt-tools** — 离线串行多专家决策系统，零硬编码、全自动适配。

---

## 功能

| 功能 | 说明 |
|------|------|
| 💰 智能报价 | 基于 rule-based 引擎的精确 CNC 报价（非 LLM 估算） |
| 🏛️ 专家会议 | 串行多专家（CFO/BI/工艺/战略/CEO），一票否决+CEO 覆写 |
| 🔍 冲突检查 | 10 条硬规则 + LLM 软规则，自动拦截不可行工艺组合 |
| 📊 历史查询 | SQLite 客户订单数据库，BI 专家有硬数据支撑 |
| 🔗 审计链 | 哈希链防篡改审计日志 |
| 🌐 Web 界面 | FastAPI + HTML，REST API 可供外部系统调用 |

## 系统要求

| 组件 | 最低 | 推荐 |
|------|------|------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 2 GB | 10 GB |
| Python | 3.10+ | 3.10 |
| Ollama | 最新版 | 最新版 |
| 模型 | qwen2.5:1.5b | qwen2.5:3b |

## 快速开始

### 方式 1: 源码运行 (Linux/macOS)

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 拉取模型
ollama pull qwen2.5:3b

# 3. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 启动
python app/main.py

# 5. 访问
open http://localhost:7861
```

### 方式 2: Docker 一键部署

```bash
# 构建并启动（含 Ollama）
docker compose up -d

# 等待模型拉取完成后访问
open http://localhost:7861
```

### 方式 3: Windows EXE

```bash
# 构建 EXE
pip install pyinstaller
pyinstaller union_by_ni.spec

# 复制到 Windows (需先安装 Ollama 并拉取模型)
# 双击 deploy/start_windows.bat
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 界面 |
| `/api/chat` | POST | 对话/报价/专家会议 |
| `/api/status` | GET | 系统状态 |
| `/api/conflict-check` | GET | 工艺冲突检测 |
| `/api/audit` | GET | 审计链查询+验证 |

### API 示例

```bash
# 报价
curl -X POST http://localhost:7861/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"6061铝合金法兰 50件 阳极氧化 报价"}'

# 冲突检查
curl "http://localhost:7861/api/conflict-check?material=304&surface_treatment=阳极氧化"
```

## 项目结构

```
cnc-ai-brain/
├── app/main.py                  # FastAPI + HTML 主入口
├── src/
│   ├── core/                    # 环境探测、模型自适应、Skill 注册
│   ├── neuro_core/             # 串行多专家引擎、冲突检查
│   ├── ai_engine/              # Ollama HTTP 封装
│   ├── runtime/                # 事件总线、报价适配、Skill 注册、历史查询
│   └── safety/                 # 审计日志 (SQLite 哈希链)
├── config/
│   ├── experts/ (5 YAML)       # CFO/BI/工艺/战略/CEO
│   └── skills/  (4 YAML)       # 报价/CAD/冲突检查/历史查询
├── deploy/                     # 部署脚本
├── Dockerfile                  # Docker 构建
├── docker-compose.yml          # 一键部署 (Ollama + App)
├── union_by_ni.spec            # PyInstaller 打包
└── requirements.txt            # Python 依赖
```

## 专家-Skill 联动

| 专家 | 调用 Skill | 数据来源 |
|------|-----------|----------|
| CFO | `quote_calculate` | 本地 rule-based 引擎 |
| BI | `history_lookup` | SQLite 订单数据库 |
| 工艺总监 | `conflict_check` | 10 条硬规则库 |

> 专家的每一句判断，都有硬数据支撑。

## 作者

- **作者**: timo.cao
- **邮箱**: miscdd@163.com
- **生成**: 大帅教练系统 (dashuai coach)
- **许可**: 商业闭源

---

*“说人话，做零件” — Union·由你*
