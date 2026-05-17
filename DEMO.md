# CNC AI 工艺大脑 v11.0.1 — 30秒看懂

## 这是什么？
一个全离线 AI 系统，装在工控机上。不联网、不调云API、数据不出车间。
输入材料和数量，它算报价、检工艺冲突、开专家会议做决策。

## 一句话价值
> 帮 CNC 工厂老板在 1 秒内算报价，70 秒内做接单决策。

## 3分钟上手

```bash
# 1. 启动
cd ~/projects/cnc-ai-brain
python3 app/main.py
# → http://localhost:7861

# 2. 试试这些
# 报价
curl -X POST http://localhost:7861/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"6061铝合金法兰 50件 阳极氧化 报价"}'

# 冲突检查
curl "http://localhost:7861/api/conflict-check?material=304&surface_treatment=阳极氧化"

# 专家会议
curl -X POST http://localhost:7861/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"深圳智造科技 钛合金TC4法兰 10件 IT5 预算5万 能接吗"}'

# 自检
curl http://localhost:7861/api/health

# 仪表盘
浏览器打开 http://localhost:7861/api/dashboard
```

## 5个演示场景

| # | 场景 | 输入 | 预期结果 |
|---|------|------|----------|
| 1 | 常规报价 | 6061法兰 50件 阳极氧化 | ¥7,656 秒出 |
| 2 | 钛合金报价 | 钛合金TC4 10件 | ¥6,344 (5.4x倍) |
| 3 | 冲突阻断 | 304法兰 阳极氧化 | ❌ 工艺冲突 |
| 4 | 冲突修复 | 304法兰 钝化 | ¥1,813 正常 |
| 5 | 专家会议 | 钛合金TC4 IT5 5万 能接? | 70s 后 REJECTED |

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 推理 | qwen2.5:3b (Ollama) | 全本地, 零API费 |
| 报价 | 纯Python规则引擎 | <1s, 5种材料 |
| 冲突 | 10条硬规则 + LLM | 零外部依赖 |
| 审计 | SQLite 哈希链 | 防篡改 |
| 前端 | FastAPI + HTML | 330行, 无框架 |
| 部署 | Docker / EXE / systemd | 三选一 |

## 部署

```bash
# systemd (开机自启)
sudo cp deploy/cnc-brain.service /etc/systemd/system/
sudo systemctl enable --now cnc-brain

# Docker
docker-compose up -d

# Windows
deploy/start_windows.bat
```

## 架构

```
用户输入 → 报价路径(<1s) → 纯Python计算 → 返回
         → 冲突路径(<1s) → 10硬规则+LLM → 阻断/放行
         → 专家路径(~70s) → 3专家串行+CEO裁决 → 决策报告
                            ↓
                    SQLite审计哈希链 (防篡改)
```

## 作者
- 作者: timo.cao
- 邮箱: miscdd@163.com
- 生成: 大帅教练系统 (dashuai coach)
