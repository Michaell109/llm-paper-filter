# 📚 Paper Find Agent (大模型驱动的自动化文献检索调研助手)

> 💡 **致谢与声明**：
> - 本项目基于 [LaugHan/paper-find-agent](https://github.com/LaugHan/paper-find-agent) 进行二次开发与重构。

一个高度工程化的学术论文爬取与智能筛选系统。只需在配置文件中写下一段自然语言的“研究需求描述”，Agent 即可自动提取检索词，跨多个顶级学术数据库（OpenReview, Arxiv, OpenAlex）抓取论文，并使用大语言模型（如 DeepSeek）进行高并发精读与打分，最终生成一份包含中文摘要和筛选理由的交互式 HTML 报告。

## ✨ 核心特性

- **🧠 意图理解与漏斗过滤**：LLM 自动将大白话需求转化为 5-8 个精准学术搜索词，执行“粗搜”后再逐篇阅读摘要进行“精筛”。
- **🎓 极广的数据源覆盖**：
  - **OpenReview**: 实时抓取 ICLR, NeurIPS, ICML, ACL 等顶会（含审稿期论文）。
  - **OpenAlex / Semantic Scholar**: 覆盖 CVPR, ECCV, TPAMI, IROS 等传统视觉/机器人顶会，甚至包含 Nature, Cell 等生物医学期刊（免 API Key，不限流）。
  - **Arxiv**: 预印本抓取，并自动请求 Semantic Scholar 过滤掉低引用（<5）的水文。
- **⚡ 高并发推理**：原生支持 asyncio 并发请求 LLM（默认 10 并发），数百篇论文筛选仅需数分钟。
- **🗂️ 模块化配置架构**：将 API、检索目标、研究描述解耦至独立的 Python 配置文件，支持一键切换不同的研究方向。
- **💾 绝对的科研可追溯性**：每次运行自动生成时间戳文件夹，完整备份原始数据、过滤数据、HTML 报告，以及**实际使用的 Config 和 Prompt 文件**。

---

## 🛠️ 1. 安装与配置 (Installation)

### 1.1 安装依赖环境
推荐使用 Python 3.8+。在终端中运行以下命令安装所需依赖：

```bash
pip install openreview-py arxiv pandas tqdm openai requests aiohttp

```

### 1.2 配置 API Key

本项目默认使用 SiliconFlow 平台提供的 DeepSeek 模型。你需要获取一个免费的 API Key：

1. 访问 [SiliconFlow](https://cloud.siliconflow.cn/) 注册并获取 API Key。
2. 在终端中配置环境变量（或直接在 `configs/default_config.py` 中硬编码）：

```bash
# Linux / macOS
export SILICON_API_KEY="sk-你的真实API_KEY"

```

---

## 🚀 2. 使用方法与命令 (Usage)

由于采用了高级配置架构，你的所有默认设置（包括长篇的研究方向描述 `DESCRIPTION`）都可以写在 `configs/default_config.py` 中。

### 基础运行 (日常深度研究)

最简单的方式，**无需敲任何额外参数**，程序会自动读取默认配置文件里的 `DESCRIPTION` 并开始全流程自动化检索：

```bash
python main.py

```

### 命令行临时覆盖 (临时起意速查)

如果你突然有了一个小灵感，不想去改配置文件，可以用 `-d` 参数**最高优先级覆盖**配置里的描述：

```bash
# 临时查一下其他方向，并指定会议和年份
python main.py -d "我想找关于 LLM 评估稳定性的最新论文" -y 2024,2025 -c ACL,EMNLP

```

### 实用高级命令

| 命令用法 | 说明 |
| --- | --- |
| `python main.py --config configs/rl_config.py` | **【推荐】** 使用指定的配置文件运行（非常适合在多个不同研究方向间无缝切换）。 |
| `python main.py --preview-prompts` | 仅在终端预览当前的 Prompt 模板内容，检查打分标准，**执行后直接退出**。 |
| `python main.py --skip-crawl -o "./results/run_xxx"` | **跳过爬取**。直接去指定的历史时间戳文件夹里读取原始数据重新打分（常用于调严/调宽 Prompt 后重跑）。 |
| `python main.py --skip-filter` | **跳过 LLM 筛选**。只利用关键词爬取会议，囤积原始论文数据集。 |
| `python main.py --html-only -o "./results/run_xxx"` | 仅根据文件夹内已有的 CSV 数据重新渲染生成精美的 HTML 网页报告。 |

---

## 🔄 3. 算法流程 (Algorithm Pipeline)

本项目采用经典的 **“宽进严出”漏斗式过滤模型**：

```text
[用户输入研究需求描述 (Config 或 -d 覆盖)]
       │
       ▼
🧠 步骤 1: LLM 意图转化 (Prompt Generator)
       ├─ LLM 生成 5-8 个交叉维度的纯文本学术搜索词
       └─ LLM 注入研究描述，生成带有思维链(CoT)的严格审稿规则
       │
       ▼
📚 步骤 2: 多源自动化粗搜 (Crawlers)
       ├─ 🤖 OpenReview: 获取 AI 顶会 (ICLR/ICML 等) 最新提交
       ├─ 🌐 OpenAlex: 获取非 OpenReview 顶会/期刊 (CVPR/IROS/Nature等)
       ├─ 📄 Arxiv: 按年份检索，并调用 Semantic Scholar 查引用量过滤水文
       └─ 🔄 数据清洗: 标题统一化与跨平台自动去重
       │
       ▼
🎯 步骤 3: 高并发智能精筛 (LLM Fine Filter)
       ├─ 并发请求 LLM 逐篇阅读论文 Abstract
       ├─ LLM 输出中文分析理由 (Reasoning)
       └─ 严格判定是否符合需求，剔除边缘提及的论文，并翻译摘要
       │
       ▼
💾 步骤 4: 结果存档与可视化 (Outputs)
       ├─ 创建 results/run_YYYY-MM-DD_HH-MM-SS/ 时间戳隔离文件夹
       ├─ 备份: used_config.py 和 used_filter_prompt.txt
       ├─ 数据: papers_raw.csv (粗搜结果) & papers_filtered.csv (精筛结果)
       └─ 可视化: papers_report.html (支持搜索、按会议筛选的精美交互式报告)

```

---

## ⚙️ 4. 配置文件参数说明 (Config)

打开 `configs/default_config.py`，你将看到以下核心配置项：

| 参数 | 说明 | 示例 / 默认值 |
| --- | --- | --- |
| `DESCRIPTION` | **核心！** 你的详细研究需求、技术栈和硬性排除条件。支持多行大白话。 | `"我的方向是机器人强化学习，必须是物理实体操作..."` |
| `API_KEY` | LLM 的密钥。 | `os.getenv("SILICON_API_KEY", "sk-xxx")` |
| `MODEL_NAME` | 用来做推理筛选的大模型。 | `"deepseek-ai/DeepSeek-V3.2"` |
| `YEARS` | 要检索的论文年份列表。 | `[2024, 2025]` |
| `CONFERENCES` | 目标会议或期刊的官方缩写。 | `['ICLR', 'CVPR', 'IROS']` |
| `CRAWL_ARXIV` | 是否在 Arxiv 预印本库中进行检索。 | `True` |
| `OPENALEX_EMAIL` | OpenAlex 官方要求。填入邮箱即可免 Key 进高速池防限流。 | `"your_email@example.com"` |
| `CONCURRENCY` | 异步请求 LLM 的并发数。数值越高筛选越快，但需注意 API 速率限制。 | `10` |

---

## 💡 5. 如何切换到其他领域/方向？

得益于模块化的设计，**你不需要修改任何复杂的 Python 逻辑代码或 Prompt 模板文件**，只需要**新建一个属于它自己的配置文件**即可。

### 示例：检索医学文献

**第一步：新建配置文件**
在 `configs/` 文件夹下新建一个文件，比如叫 `configs/biology_config.py`，然后复制以下内容进去：

```python
import os

# 1. 用自然语言写下医学研究需求（越详细越好，说明要什么，不要什么）
DESCRIPTION = """
我的研究方向是基于单细胞 RNA 测序（scRNA-seq）的肿瘤微环境免疫细胞分型。
我重点关注运用深度学习模型（尤其是图神经网络 GNN 或 Transformer）来进行细胞聚类和基因调控网络推断的研究。
【硬性要求】：必须是应用于人类癌症数据的计算生物学/生物信息学论文。
如果是纯计算机视觉的医学图像分割（如 MRI/CT 识别），或者只是综述文章，请判定为不相关并排除。
"""

# 2. 爬虫目标设置（换成生物医学领域的顶级期刊）
YEARS = [2023, 2024, 2025]
CONFERENCES = ['Nature', 'Cell', 'Science', 'Bioinformatics', 'Lancet']
CRAWL_ARXIV = False  # 医学通常看发表的，关闭 arxiv

# 3. 基础运行配置
API_KEY = os.getenv("SILICON_API_KEY", "sk-你的API密钥")
BASE_URL = "https://api.siliconflow.cn/v1/"
MODEL_NAME = "deepseek-ai/DeepSeek-V3.2"
OPENALEX_EMAIL = "your_email@example.com"  # OpenAlex 涵盖了庞大的 PubMed 医学库
CONCURRENCY = 10
OUTPUT_DIR = "./results"

```

**第二步：运行该配置**
在终端中执行以下命令，告诉 Agent 读取这个新文件：

```bash
python main.py --config configs/biology_config.py

```

程序就会自动提取医学关键词，去 OpenAlex 抓取 Nature/Cell 的论文，并用医学审稿人的严苛标准为你输出最终的中文 HTML 报告！

---

## 🤝 贡献与感谢

本项目融合了爬虫工程、异步 IO 与高级 Prompt Engineering (思维链打分)。

* 再次感谢 [LaugHan/paper-find-agent](https://www.google.com/url?sa=E&source=gmail&q=https://github.com/LaugHan/paper-find-agent) 的开源代码提供的底层框架支持。
* 感谢 [OpenReview](https://openreview.net/) / [Arxiv](https://arxiv.org/) / [OpenAlex](https://openalex.org/) 提供的开放学术数据接口。
* 感谢大语言模型赋予的强大语义过滤能力。
