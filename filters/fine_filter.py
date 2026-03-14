"""
LLM 筛选器 - 支持并发推理
"""
import asyncio
from typing import List
from tqdm import tqdm

from config import LLMConfig
from crawlers.base import PaperData
from .base import SiliconFlowClient, parse_xml_response


class FineFilter:
    """LLM 筛选器（支持并发）"""
    
    def __init__(self, config: LLMConfig, prompt_template: str = None, concurrency: int = 10):
        self.client = SiliconFlowClient(config)
        self.system_prompt = "你是一个严谨的学术论文筛选助手。"
        self.concurrency = concurrency
        
        if prompt_template:
            self.prompt_template = prompt_template
        else:
            # 如果没有传入 prompt，尝试从文件加载
            try:
                from prompt_generator import load_prompt_template
                self.prompt_template = load_prompt_template("filter_template.txt")
            except Exception as e:
                print(f"⚠️ 初始化 FineFilter 失败：{e}")
                self.prompt_template = ""
    
    def build_prompt(self, title: str, abstract: str) -> str:
        """构建筛选 prompt"""
        return self.prompt_template.format(title=title, abstract=abstract)
    
    def filter_papers(
        self,
        papers: List[PaperData],
        sleep_seconds: float = 0.0  # 并发模式下不需要 sleep
    ) -> List[PaperData]:
        """
        批量筛选论文（并发）
        
        Args:
            papers: 待筛选论文列表
            sleep_seconds: 已废弃，保留参数兼容性
        
        Returns:
            通过筛选的论文列表
        """
        print(f"\n🔍 [LLM筛选] 开始筛选 {len(papers)} 篇论文（并发数: {self.concurrency}）...")
        
        # 构建所有 prompts
        prompts = [self.build_prompt(p.title, p.abstract) for p in papers]
        
        # 并发调用
        results = asyncio.run(self._filter_batch_async(prompts, papers))
        
        print(f"   ✅ 筛选完成，保留 {len(results)} 篇论文")
        return results
    
    async def _filter_batch_async(
        self, 
        prompts: List[str], 
        papers: List[PaperData]
    ) -> List[PaperData]:
        """异步批量筛选"""
        
        # 使用 tqdm 显示进度
        pbar = tqdm(total=len(prompts), desc="筛选进度")
        
        results = []
        batch_size = self.concurrency * 2  # 每批处理的数量
        
        for i in range(0, len(prompts), batch_size):
            batch_prompts = prompts[i:i + batch_size]
            batch_papers = papers[i:i + batch_size]
            
            # 并发调用这一批
            responses = await self.client.call_batch_async(
                batch_prompts,
                self.system_prompt,
                concurrency=self.concurrency
            )
            
            # 处理响应
            for paper, response in zip(batch_papers, responses):
                if response:
                    is_relevant, reason, abstract_zh = parse_xml_response(response)
                    if is_relevant:
                        paper.reason_zh = reason
                        paper.abstract_zh = abstract_zh
                        results.append(paper)
                pbar.update(1)
            
            # 短暂休息避免限流
            await asyncio.sleep(0.5)
        
        pbar.close()
        return results
