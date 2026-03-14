"""
Paper Pipeline 配置管理
"""
import os
import importlib.util
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class LLMConfig:
    """LLM 模型配置"""
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 4096

class Config:
    def __init__(self, config_path: str = "configs/default_config.py", **overrides):
        # 记录当前使用的配置文件路径，方便后续备份
        self.config_path = config_path
        
        spec = importlib.util.spec_from_file_location("user_config", config_path)
        user_config = importlib.util.module_from_spec(spec)
        if spec and spec.loader:
            spec.loader.exec_module(user_config)
        
        self.description = overrides.get('description') or getattr(user_config, 'DESCRIPTION', "")
        self.years = overrides.get('years', getattr(user_config, 'YEARS', [2024, 2025]))
        self.conferences = overrides.get('conferences', getattr(user_config, 'CONFERENCES', []))
        self.crawl_arxiv = overrides.get('crawl_arxiv', getattr(user_config, 'CRAWL_ARXIV', True))
        self.arxiv_max_results = getattr(user_config, 'ARXIV_MAX_RESULTS', 500)
        self.openalex_email = getattr(user_config, 'OPENALEX_EMAIL', "bot@example.com")
        self.concurrency = getattr(user_config, 'CONCURRENCY', 10)
        
        # ================== 自动时间戳文件夹逻辑 ==================
        base_output_dir = getattr(user_config, 'OUTPUT_DIR', "./results")
        
        if 'output_dir' in overrides and overrides['output_dir'] is not None:
            # 如果命令行显式传入了 -o，就精确使用传入的路径（方便 skip-crawl 读取旧数据）
            self.output_dir = overrides['output_dir']
        else:
            # 否则，自动创建带时间戳的子文件夹 (例如: results/run_2026-03-14_09-42-00)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.output_dir = os.path.join(base_output_dir, f"run_{timestamp}")
            
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        # ==========================================================
        
        self.raw_papers_path = os.path.join(self.output_dir, "papers_raw.csv")
        self.output_csv_path = os.path.join(self.output_dir, "papers_filtered.csv")
        self.output_html_path = os.path.join(self.output_dir, "papers_report.html")
        
        self.large_llm = LLMConfig(
            api_key=getattr(user_config, 'API_KEY', ""),
            base_url=getattr(user_config, 'BASE_URL', ""),
            model_name=getattr(user_config, 'MODEL_NAME', "")
        )

def load_config(config_path="configs/default_config.py", **overrides) -> Config:
    return Config(config_path, **overrides)