"""
OpenReview 爬虫 - 支持 ICLR, NeurIPS, ICML, ACL
支持关键词预过滤
"""
import openreview
from tqdm import tqdm
from typing import List, Optional
from .base import PaperData


def get_content_val(content, key, default=''):
    """
    兼容 OpenReview V1 和 V2 API 的内容提取
    """
    if not content:
        return default
    val = content.get(key)
    if val is None:
        return default
    if isinstance(val, dict) and 'value' in val:
        return val['value']
    return val


def matches_keywords(title: str, abstract: str, paper_keywords: List[str], search_keywords: List[str]) -> bool:
    """检查论文是否匹配搜索关键词"""
    if not search_keywords:
        return True  
    
    full_text = f"{title} {abstract} {' '.join(paper_keywords)}".lower()
    for kw in search_keywords:
        if kw.lower() in full_text:
            return True
    return False


class OpenReviewCrawler:
    """OpenReview 论文爬虫"""
    
    def __init__(self, year: int):
        self.client = openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net'
        )
        self.year = str(year)
    
    def _get_venue_id(self, conf_name: str) -> Optional[str]:
        """获取会议的 venue ID"""
        conf = conf_name.upper()
        y = self.year
        
        if conf == 'ICLR':
            return f'ICLR.cc/{y}/Conference'
        elif conf in ['NEURIPS', 'NIPS']:
            return f'NeurIPS.cc/{y}/Conference'
        elif conf == 'ICML':
            return f'ICML.cc/{y}/Conference'
        elif conf == 'ACL':
            return f'aclweb.org/ACL/{y}'
        elif conf == 'TRL' or conf == 'TMLR':
            return 'TMLR'
        
        return None
    
    def _get_acl_invitations(self) -> List[str]:
        """获取 ACL ARR 的 invitation IDs"""
        y = self.year
        if y == '2024':
            months = ['February', 'April', 'June', 'October']
        elif y == '2025':
            months = ['May', 'July', 'October']
        else:
            months = ['February', 'April', 'June', 'October', 'May', 'July']
        
        return [f'aclweb.org/ACL/ARR/{y}/{m}/-/Submission' for m in months]
    
    def crawl(self, conf_name: str, keywords: Optional[List[str]] = None) -> List[PaperData]:
        conf_upper = conf_name.upper()
        submissions = []
        
        if conf_upper == 'ACL':
            invitations = self._get_acl_invitations()
            for inv in invitations:
                print(f"🔍 [OpenReview] 获取 {inv} ...")
                try:
                    batch = self.client.get_all_notes(invitation=inv)
                    print(f"   ✅ 获取到 {len(batch)} 篇")
                    submissions.extend(batch)
                except Exception as e:
                    if "Forbidden" in str(e) or "NotFoundError" in str(e):
                        print(f"   ⚠️ 无法访问 {inv}")
                    else:
                        print(f"   ❌ 错误: {e}")
        else:
            venue_id = self._get_venue_id(conf_name)
            if not venue_id:
                print(f"⚠️ 未配置会议: {conf_name}")
                return []
            
            print(f"🔍 [OpenReview] 获取 {venue_id} ...")
            try:
                submissions = self.client.get_all_notes(
                    content={'venueid': venue_id}
                )
                print(f"   ✅ 获取到 {len(submissions)} 篇")
            except Exception as e:
                if "Forbidden" in str(e) or "NotFoundError" in str(e):
                    print(f"   ⚠️ 无法访问 {venue_id}")
                else:
                    print(f"   ❌ 错误: {e}")
                return []
        
        if not submissions:
            print(f"⚠️ {conf_name} {self.year} 未获取到论文")
            return []
        
        results = []
        seen = set()
        filtered_count = 0
        
        for note in tqdm(submissions, desc=f"解析 {conf_name} {self.year}"):
            if note.id in seen:
                continue
            seen.add(note.id)
            
            content = note.content
            title = get_content_val(content, 'title')
            abstract = get_content_val(content, 'abstract')
            
            if not title or not abstract:
                continue
            
            kw_list = get_content_val(content, 'keywords', [])
            if not isinstance(kw_list, list):
                kw_list = []
            
            if keywords and not matches_keywords(title, abstract, kw_list, keywords):
                filtered_count += 1
                continue
            
            keywords_str = ", ".join(kw_list)
            authors_list = get_content_val(content, 'authors', [])
            authors_str = ", ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)
            
            author_ids = get_content_val(content, 'authorids', [])
            institutions = set()
            if isinstance(author_ids, list):
                for uid in author_ids:
                    if '@' in str(uid):
                        institutions.add(str(uid).split('@')[-1])
            institutions_str = ", ".join(institutions)
            
            paper = PaperData(
                title=str(title).strip(),
                abstract=str(abstract).strip().replace('\n', ' '),
                authors=authors_str,
                institutions=institutions_str,
                venue=f"{conf_name} {self.year}",
                url=f"https://openreview.net/forum?id={note.id}",
                year=self.year,
                keywords=keywords_str
            )
            results.append(paper)
        
        if keywords:
            print(f"   🔑 关键词过滤: {filtered_count} 篇被过滤")
        print(f"   📊 {conf_name} {self.year}: 共 {len(results)} 篇论文")
        
        return results