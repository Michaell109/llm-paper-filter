"""
Semantic Scholar 爬虫 - 支持 CVPR, ECCV, TPAMI, IROS 等非 OpenReview 会议
"""
import requests
import time
from typing import List, Optional
from .base import PaperData

class SemanticScholarCrawler:
    """Semantic Scholar 会议爬虫"""
    
    def __init__(self, min_citations: int = 0):
        self.search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        self.min_citations = min_citations

    def crawl(self, conf_name: str, year: int, keywords: Optional[List[str]] = None, max_results: int = 100) -> List[PaperData]:
        if not keywords:
            print(f"⚠️ [Semantic Scholar] 抓取 {conf_name} 必须提供关键词")
            return []

        # 将关键词用 | 组合，符合 SS API 的查询逻辑
        query = " | ".join(keywords)
        
        params = {
            "query": query,
            "venue": conf_name.upper(),
            "year": str(year),
            "limit": max_results,
            "fields": "title,abstract,authors,venue,year,url,citationCount"
        }

        print(f"🔍 [Semantic Scholar] 获取 {conf_name} {year} ...")
        results = []

        try:
            response = requests.get(self.search_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                print(f"   ✅ 获取到 {len(papers)} 篇")

                for p in papers:
                    # 过滤掉没有摘要的论文，因为 LLM 筛选强依赖摘要
                    if not p.get('abstract') or not p.get('title'):
                        continue

                    if p.get('citationCount', 0) < self.min_citations:
                        continue

                    authors = [a.get('name', '') for a in p.get('authors', [])]

                    paper = PaperData(
                        title=p['title'],
                        abstract=p['abstract'].replace('\n', ' '),
                        authors=", ".join(authors),
                        institutions="N/A",
                        venue=f"{p.get('venue', conf_name)} {year}",
                        url=p.get('url', ''),
                        year=str(year),
                        keywords=""
                    )
                    results.append(paper)
            elif response.status_code == 429:
                print("   ⚠️ Semantic Scholar API 限流，请稍后再试")
            else:
                print(f"   ❌ 错误: HTTP {response.status_code}")

        except Exception as e:
            print(f"   ❌ 获取失败: {e}")

        # 基础限流保护
        time.sleep(1.5)
        return results