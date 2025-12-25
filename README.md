# 🧠 DailyKnowledge

> 每日 AI 知识推送系统 - 基于艾宾浩斯遗忘曲线的间隔重复学习

[![Daily Knowledge Push](https://github.com/YHChen0511/DailyKnowledge/actions/workflows/daily_knowledge.yml/badge.svg)](https://github.com/YHChen0511/DailyKnowledge/actions/workflows/daily_knowledge.yml)

## 📖 项目简介

DailyKnowledge 是一个自动化的 AI 知识学习系统，每天推送一封邮件包含：

- **1 个新 AI 知识点** - 由 LLM 根据你的背景**动态生成**适合的主题
- **N 个旧知识复习题** - 基于艾宾浩斯遗忘曲线算法，智能安排复习

## ✨ 特性

- 🚀 **动态主题生成** - LLM 根据用户画像（如博士生背景）智能推荐学习主题，永不重复
- 🎯 **个性化内容** - 根据你的研究方向、知识水平定制内容深度
- 🤖 **LLM 驱动** - 使用 Gemini API 生成研究生级别的深度内容
- 📊 **科学复习** - 艾宾浩斯遗忘曲线 (1, 2, 4, 7, 15, 30, 60 天间隔)
- 📧 **精美邮件** - Markdown 渲染为响应式 HTML
- 🔄 **完全自动化** - GitHub Actions 定时触发，零运维
- 💾 **轻量级存储** - SQLite 单文件数据库，易于备份

## 🎯 两种选题模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **动态模式** (默认) | LLM 根据用户画像智能生成主题 | 研究生/研究员，需要前沿、个性化内容 |
| **静态模式** | 从预定义的 topics.json 列表中选择 | 入门学习，需要系统性覆盖基础知识 |

## 📁 项目结构

```
DailyKnowledge/
├── main.py                 # 主入口程序
├── config.py               # 配置管理
├── user_profile.py         # 👤 用户画像配置（编辑这个！）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── core/
│   ├── selector.py         # 选题逻辑（动态/静态 + 复习）
│   ├── generator.py        # LLM 内容生成
│   ├── messenger.py        # 邮件发送
│   └── recorder.py         # 数据库更新
├── database/
│   ├── models.py           # 数据库模型
│   └── knowledge.db        # SQLite 数据库
├── prompts/
│   ├── topic_generator.py  # 🆕 动态主题生成 Prompt
│   ├── newsletter.py       # 新知识生成 Prompt
│   └── examiner.py         # 复习题生成 Prompt
├── data/
│   └── topics.json         # 知识主题库 (静态模式备用)
└── .github/workflows/
    └── daily_knowledge.yml # GitHub Actions 配置
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/YHChen0511/DailyKnowledge.git
cd DailyKnowledge
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置用户画像 ⭐

编辑 `user_profile.py`，填入你的背景信息：

```python
USER_PROFILE = """
### 基本信息
- **身份**：人工智能方向博士一年级研究生
- **研究方向**：大语言模型 / 多模态学习

### 知识背景
- **数学基础**：研究生水平
- **编程能力**：Python 熟练，PyTorch 日常使用

### 学习目标
- 跟踪 AI 领域前沿进展
- 夯实理论基础
"""

# 感兴趣的方向（权重更高）
INTERESTS = ["大语言模型", "多模态学习", "高效推理"]
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

需要配置的变量：

| 变量 | 必需 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | OpenAI API Key（或兼容服务的密钥） |
| `OPENAI_BASE_URL` | ❌ | 自定义 API 端点（默认 OpenAI 官方） |
| `OPENAI_MODEL` | ❌ | 模型名称（默认 `gpt-4o-mini`） |
| `SMTP_SERVER` | ✅ | SMTP 服务器地址 |
| `SMTP_PORT` | ✅ | SMTP 端口 (通常为 587) |
| `SMTP_USERNAME` | ✅ | 邮箱用户名 |
| `SMTP_PASSWORD` | ✅ | 邮箱应用专用密码 |
| `EMAIL_FROM` | ✅ | 发件人地址 |
| `EMAIL_TO` | ✅ | 收件人地址 |

**支持的 API 服务：**

```bash
# OpenAI 官方
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepSeek
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# Azure OpenAI
OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment

# 本地 Ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.2
```

### 5. 本地测试

```bash
# 查看当前状态
python main.py --status

# 测试 API 连接
python main.py --test

# 空运行（不发邮件、不更新数据库）- 使用动态模式
python main.py --dry-run

# 空运行 - 使用静态主题列表
python main.py --dry-run --static

# 正式运行
python main.py
```

## ⚙️ GitHub Actions 配置

### 配置 Secrets

在仓库的 `Settings > Secrets and variables > Actions` 中添加以下 secrets：

| Secret | 必需 | 说明 |
|--------|------|------|
| `OPENAI_API_KEY` | ✅ | API 密钥 |
| `OPENAI_BASE_URL` | ❌ | 自定义端点（可选） |
| `OPENAI_MODEL` | ❌ | 模型名称（可选） |
| `SMTP_SERVER` | ✅ | SMTP 服务器 |
| `SMTP_PORT` | ✅ | SMTP 端口 |
| `SMTP_USERNAME` | ✅ | 邮箱用户名 |
| `SMTP_PASSWORD` | ✅ | 应用专用密码 |
| `EMAIL_FROM` | ✅ | 发件人 |
| `EMAIL_TO` | ✅ | 收件人 |

### 触发时间

默认配置为每天北京时间 08:00 运行 (UTC 00:00)。

可以在 `.github/workflows/daily_knowledge.yml` 中修改 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 时间
```

### 手动触发

在 GitHub Actions 页面可以手动触发 workflow，支持 `dry_run` 选项。

## 🎨 知识类别 (动态模式)

动态模式下，LLM 会从以下方向中智能选题：

| 方向 | 说明 | 示例 |
|------|------|------|
| 🧠 Theory | 数学与理论基础 | KL Divergence, ELBO |
| 🏗️ Architecture | 模型架构设计 | Transformer, MoE, SSM |
| ⚡ Training | 训练技术与优化 | Mixed Precision, FSDP |
| 🎯 Alignment | 对齐与安全 | RLHF, DPO, Constitutional AI |
| 🚀 Efficiency | 推理与部署优化 | vLLM, Quantization |
| 🌈 Multimodal | 多模态学习 | CLIP, Diffusion |
| 🤖 Agent | Agent 与推理 | CoT, ReAct, Tool Use |
| 🎨 Generation | 内容生成 | ControlNet, LoRA |
| 💻 Application | 实际应用 | RAG, Code Generation |
| 🔮 Frontier | 前沿研究 | World Models, Reasoning |

## 📚 静态知识库 (备用)

| 类别 | Emoji | 内容方向 | 示例 |
|------|-------|----------|------|
| Foundations | 🟢 | 数学与底层原理 | KL Divergence, Backprop |
| Engineering | 🔵 | 落地与系统优化 | vLLM, FlashAttention, ONNX |
| SOTA | 🟣 | 前沿技术点 | LoRA, MoE, RAG, DPO |
| Reasoning | 🟠 | Agent 与 Prompt | CoT, ReAct, Tool Use |
| History | 🟡 | 历史与行业八卦 | ImageNet, AlphaGo, GPT |

## 📊 数据库 Schema

```sql
CREATE TABLE knowledge_cards (
    id INTEGER PRIMARY KEY,
    topic TEXT UNIQUE,        -- 知识点名称
    category TEXT,            -- 分类
    summary TEXT,             -- LLM 生成的速记总结
    created_at DATE,          -- 首次学习日期
    next_review_date DATE,    -- 下次复习日期
    review_stage INTEGER      -- 艾宾浩斯阶段 (0-6)
);
```

## 🔧 自定义扩展

### 配置用户画像

编辑 `user_profile.py` 来个性化知识推荐：

```python
# 描述你的背景，LLM 会据此调整内容深度
USER_PROFILE = """
- 身份：博士生/工程师/爱好者
- 研究方向：你的方向
- 知识背景：数学/编程水平
"""

# 感兴趣的方向（会增加权重）
INTERESTS = ["大语言模型", "多模态"]

# 已经很熟悉的主题（会跳过）
SKIP_TOPICS = ["基础PyTorch", "基础Python"]

# 难度范围 (1-10)
MIN_DIFFICULTY = 5
MAX_DIFFICULTY = 9
```

### 添加静态知识点 (静态模式)

编辑 `data/topics.json`，添加新的主题：

```json
{
  "topic": "Your Topic Name",
  "category": "Foundations",
  "tags": ["tag1", "tag2"]
}
```

### 修改复习间隔

编辑 `config.py` 中的 `REVIEW_INTERVALS`：

```python
REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30, 60]  # 天数
```

### 自定义邮件模板

修改 `core/messenger.py` 中的 `EMAIL_STYLES` 和 HTML 模板。

## 📝 命令行参数

```bash
python main.py [OPTIONS]

Options:
  --dry-run      空运行，不发送邮件也不更新数据库
  --static       使用静态主题列表 (而非 LLM 动态生成)
  --skip-email   跳过邮件发送，但更新数据库
  --status       显示当前学习状态
  --test         测试 API 和邮件连接
  --init-db      仅初始化数据库
```

## 🧪 工作原理

### 动态模式流程

```
┌─────────────────────────────────────────────────┐
│  1. 读取 user_profile.py (用户画像)             │
│  2. 查询数据库 - 获取已学习主题列表              │
│  3. 调用 LLM - 生成不重复的新主题                │
│  4. 调用 LLM - 为主题生成详细内容                │
│  5. 选择到期复习的旧知识                        │
│  6. 组装邮件并发送                              │
│  7. 更新数据库记录                              │
└─────────────────────────────────────────────────┘
```

### 去重机制

系统通过以下方式确保不会重复推送相同内容：

1. **数据库查重** - 新主题生成时会排除所有已学习的主题
2. **相似性检测** - Prompt 中要求 LLM 避免语义相近的主题
3. **唯一约束** - 数据库中 topic 字段有唯一索引

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License
