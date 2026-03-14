"""
默认配置文件 (MMDetection 风格)
"""
import os

# ================= 0. 核心研究需求 =================
# 在这里写下你的默认研究描述。支持多行长文本。
DESCRIPTION = """
我的研究方向是具身智能与机器人操作（Robotic Manipulation）。
核心目标是赋予机械臂或灵巧手对未知环境和多样化物体（Generalizable Object Manipulation）的通用操作能力。

在技术栈上，我重点关注以下三大基础模型在机器人领域的应用：
1. 视觉-语言-动作模型（Vision-Language-Action Models, VLA），用于将多模态感知和自然语言指令端到端地映射为机器人的底层控制动作；
2. 视觉语言模型（Vision-Language Models, VLM），用于高级语义理解、复杂任务分解、场景常识推理和奖励函数设计；
3. 世界模型（World Models），用于物理环境的动态预测、因果表征学习以及支持强化学习的梦境训练（Dreaming/Imagination）。
在训练范式上，以强化学习（Reinforcement Learning, RL）为核心，辅以模仿学习（Imitation Learning, IL）来加速探索或提供行为先验。

【硬性否决条件：必须是物理实体/机器人任务】
论文的核心任务和实验场景必须明确应用于机器人（Robotics）或具身智能（Embodied AI）实体，如机械臂操作、灵巧手、移动抓取等物理真实或高保真仿真物理交互。
如果是纯视觉（如单纯的图像分割）、纯语言（纯 NLP）、或仅仅在虚拟非物理游戏（如 Atari、星际争霸、棋盘游戏）上测试的纯理论强化学习/世界模型论文，即使使用了上述技术栈，也请一律判定为不相关并排除。

我希望找到那些将 VLA, VLM 或 World Model 深度集成到机器人控制策略（Visuomotor Policy）中的前沿论文，特别是涉及 Sim-to-Real 迁移、多模态强化学习、或者基于世界模型的复杂物理交互任务的研究。
"""

# ================= 1. API 配置 =================
API_KEY = os.getenv("SILICON_API_KEY", "sk-这里填你的真实API_KEY")
BASE_URL = "https://api.siliconflow.cn/v1/"
MODEL_NAME = "deepseek-ai/DeepSeek-V3.2"  # 按需求更换合适的模型

# ================= 2. 爬虫全局默认配置 =================
YEARS = [2025]
CONFERENCES = [
    'ICLR', 'ICML', 'NEURIPS', 'ACL', 
    'CVPR', 'TPAMI', 'ECCV', 'IROS', 'TRL'
]
CRAWL_ARXIV = True
ARXIV_MAX_RESULTS = 500
# 👇 新增：OpenAlex 高速池邮箱。OpenAlex 无需注册。提供任意邮箱即可进入 polite pool (高速池)，避免被限流
OPENALEX_EMAIL = "your_email@example.com"

# ================= 3. 运行与输出配置 =================
CONCURRENCY = 10  
OUTPUT_DIR = "./results"