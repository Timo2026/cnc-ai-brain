# 🦞 Union·由你 — CNC AI 工艺大脑 v11.0.4
## Windows 一键部署说明

---

## 一、极速启动（1分钟）

### 要求
- Windows 10/11
- 网络（首次安装依赖需要）

### 步骤
1. **解压** 本包到任意目录（路径不要有中文）
2. **双击** `一键启动.bat`
3. **等待** 自动安装依赖（约1-2分钟）
4. **浏览器** 自动打开 http://localhost:7861
5. **开始使用！**

### 就这么简单。
不需要装 Python 以外的东西。
不需要装 Ollama。
不需要 AI 模型。
不需要 GPU。

---

## 二、有什么功能

| 功能 | 需要什么 | 说明 |
|------|----------|------|
| ✅ 一句话画STEP | 无 | "画一个法兰 外径100内径50厚20" |
| ✅ 3D实时预览 | 无 | Three.js 旋转/缩放/平移 |
| ✅ CNC报价 | 无 | 5材料梯度 / 8表面处理 |
| ✅ 工艺冲突检测 | 无 | 纯规则引擎，零延迟 |
| ✅ 上传STEP报价 | 无 | 拖拽STEP自动解析包围盒 |
| ✅ ZIP打包导出 | 无 | 包含STEP+报价+清单 |
| ✅ 离线运行 | 无 | 全部本地，无需联网 |
| ❌ AI专家会议 | Ollama | 额外功能，不影响核心使用 |

---

## 三、想升级？装Ollama加AI（可选）

如果想用 AI 对话和专家会议：

```cmd
# 1. 下载安装 Ollama
https://ollama.com/download/windows

# 2. 拉取模型（约2GB）
ollama pull qwen2.5:3b

# 3. 运行完整版（替代 Lite）
python app/main.py
```

完整版 v11.0.4 额外支持：
- 💬 AI 对话咨询
- 🏛️ 5人专家会议（CFO/工艺/战略/BI/CEO）
- 📊 审计哈希链
- ⚖️ Schema 校验

---

## 四、常见问题

**Q: 报错 "Python 没有安装"**
A: 访问 https://www.python.org/downloads/ 下载安装，勾选"Add Python to PATH"

**Q: 安装依赖很慢**
A: `一键启动.bat` 默认使用清华镜像源，如果还慢，手动运行：
```cmd
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: 报价准吗？**
A: 报价基于材料系数×重量×表面处理×数量折扣，是公开市场价的估算。
   精度约 ±30%。实际报价需人工确认。

**Q: 能脱机使用吗？**
A: 能。全部代码和依赖安装后，不需要联网。

**Q: 怎么关闭？**
A: 命令行按 Ctrl+C 或关掉命令行窗口。

---

## 五、源代码
GitHub: https://github.com/Timo2026/cnc-ai-brain
Release: https://github.com/Timo2026/cnc-ai-brain/releases/tag/v11.0.4

---

作者: timo.cao | 邮箱: miscdd@163.com
生成: 大帅教练系统 (dashuai coach) | v11.0.4
