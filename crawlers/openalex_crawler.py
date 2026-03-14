"""
OpenAlex 爬虫 - 替代 Semantic Scholar，无频次限制，免费开源
支持 CVPR, ECCV, TPAMI, IROS 等
"""
import requests
import time
from typing import List, Optional
from .base import PaperData

class OpenAlexCrawler:
    def __init__(self, email: str = "bot@example.com", min_citations: int = 0):
        self.works_url = "https://api.openalex.org/works"
        self.sources_url = "https://api.openalex.org/sources"
        self.min_citations = min_citations
        
        # 👇 动态拼接邮箱
        self.headers = {"User-Agent": f"mailto:{email}"}
        
        self.source_id_cache = {}

    def _get_source_id(self, conf_name: str) -> Optional[str]:
        """第一步：动态查询会议/期刊的 OpenAlex Source ID"""
        if conf_name in self.source_id_cache:
            return self.source_id_cache[conf_name]
            
        try:
            r = requests.get(
                self.sources_url, 
                params={"search": conf_name, "per-page": 1}, 
                headers=self.headers, 
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("results"):
                    # 提取形如 'S112836262' 的 ID
                    source_id = data["results"][0]["id"].split("/")[-1]
                    self.source_id_cache[conf_name] = source_id
                    return source_id
        except Exception as e:
            print(f"   ⚠️ 获取 {conf_name} 的 Source ID 失败: {e}")
            
        return None

    def _build_abstract(self, inverted_index: dict) -> str:
        """OpenAlex 的摘要是倒排索引格式，需要还原成普通文本"""
        if not inverted_index:
            return ""
        try:
            max_idx = max([idx for positions in inverted_index.values() for idx in positions])
            words = [""] * (max_idx + 1)
            for word, positions in inverted_index.items():
                for pos in positions:
                    words[pos] = word
            return " ".join(words).strip()
        except Exception:
            return ""

    def crawl(self, conf_name: str, year: int, keywords: Optional[List[str]] = None, max_results: int = 100) -> List[PaperData]:
        if not keywords:
            return []

        # 1. 自动获取并验证 Source ID
        source_id = self._get_source_id(conf_name)
        if not source_id:
            print(f"   ⚠️ [OpenAlex] 无法在数据库中找到会议/期刊: {conf_name}")
            return []

        # 2. 第二步：构建合法的过滤条件获取论文
        filters = [
            f"publication_year:{year}",
            f"primary_location.source.id:{source_id}",
        ]
        if self.min_citations > 0:
            filters.append(f"cited_by_count:>{self.min_citations - 1}")

        search_query = " ".join(keywords)

        params = {
            "search": search_query,
            "filter": ",".join(filters),
            "per-page": min(max_results, 200),
            "sort": "cited_by_count:desc"
        }

        print(f"🔍 [OpenAlex] 获取 {conf_name} {year} (ID: {source_id}) ...")
        results = []

        try:
            response = requests.get(self.works_url, params=params, headers=self.headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                papers = data.get("results", [])
                print(f"   ✅ 获取到 {len(papers)} 篇")

                for p in papers:
                    # 还原摘要
                    abstract = self._build_abstract(p.get('abstract_inverted_index'))
                    # LLM 筛选强依赖摘要，没有摘要的论文直接丢弃
                    if not abstract or not p.get('title'):
                        continue

                    authors = [a.get('author', {}).get('display_name', '') for a in p.get('authorships', [])]
                    
                    venue_name = conf_name
                    if p.get('primary_location') and p['primary_location'].get('source'):
                        venue_name = p['primary_location']['source'].get('display_name', conf_name)

                    paper = PaperData(
                        title=p.get('title', ''),
                        abstract=abstract,
                        authors=", ".join(filter(None, authors)),
                        institutions="N/A",
                        venue=f"{venue_name} {year}",
                        url=p.get('id', ''),  # OpenAlex ID 或者 DOI 链接
                        year=str(year),
                        keywords=""
                    )
                    results.append(paper)
            else:
                print(f"   ❌ 错误: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")

        # OpenAlex 高速池建议 100ms 间隔，这里设为 0.5s 非常安全
        time.sleep(0.5) 
        return results