"""
小模型初筛 - 使用简单 prompt 快速过滤
"""
import time
from typing import List
from tqdm import tqdm

from config import LLMConfig
from crawlers.base import PaperData
from .base import OpenAICompatibleClient, parse_xml_response


class CoarseFilter:
    """小模型初筛器"""
    
    def __init__(self, config: LLMConfig, prompt_template: str):
        """
        Args:
            config: LLM 配置
            prompt_template: 筛选 prompt 模板，包含 {title} 和 {abstract} 占位符
        """
        self.client = OpenAICompatibleClient(config)
        self.prompt_template = prompt_template
    
    def build_prompt(self, title: str, abstract: str) -> str:
        """构建筛选 prompt"""
        return self.prompt_template.format(title=title, abstract=abstract)
    
    def filter_paper(self, paper: PaperData) -> bool:
        """
        筛选单篇论文
        
        Returns:
            True 如果论文相关
        """
        prompt = self.build_prompt(paper.title, paper.abstract)
        response = self.client.call(prompt)
        
        if response:
            is_relevant, reason, abstract_zh = parse_xml_response(response)
            if is_relevant:
                paper.reason_zh = reason
                paper.abstract_zh = abstract_zh
            return is_relevant
        return False
    
    def filter_papers(
        self,
        papers: List[PaperData],
        sleep_seconds: float = 1.0
    ) -> List[PaperData]:
        """
        批量筛选论文
        
        Args:
            papers: 待筛选论文列表
            sleep_seconds: 每次调用后的等待时间
        
        Returns:
            通过筛选的论文列表
        """
        results = []
        
        print(f"\n🔍 [初筛] 开始筛选 {len(papers)} 篇论文...")
        
        for paper in tqdm(papers, desc="初筛进度"):
            if self.filter_paper(paper):
                results.append(paper)
            time.sleep(sleep_seconds)
        
        print(f"   ✅ 初筛完成，保留 {len(results)} 篇论文")
        return results
