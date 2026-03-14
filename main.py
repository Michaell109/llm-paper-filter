"""
Paper Pipeline 主入口
支持: 爬取 -> 筛选 -> HTML 生成 (每个步骤可单独跳过)
"""
import argparse
import os
import sys
import shutil  # 新增：用于复制配置文件
import pandas as pd
from typing import List, Optional

from config import Config, load_config
from crawlers import OpenReviewCrawler, ArxivCrawler, SemanticScholarCrawler, PaperData, OpenAlexCrawler
from filters import FineFilter
from prompt_generator import generate_all, load_prompt_template
from output import write_csv, write_html
from output.html_writer import write_html_from_csv


def preview_prompts():
    print("\n" + "="*60)
    print("🔍 Prompt 模板预览")
    print("="*60)
    try:
        gen_prompt = load_prompt_template("generator_template.txt")
        print("\n[1] 生成器 Prompt (prompts/generator_template.txt):")
        print("-" * 60)
        print(gen_prompt)
    except Exception as e:
        print(f"\n[1] 生成器 Prompt 读取失败: {e}")
    try:
        filter_prompt = load_prompt_template("filter_template.txt")
        print("\n[2] 筛选器 Prompt (prompts/filter_template.txt):")
        print("-" * 60)
        print(filter_prompt)
    except Exception as e:
        print(f"\n[2] 筛选器 Prompt 读取失败: {e}")
    print("\n" + "="*60)
    sys.exit(0)


def interactive_confirm_keywords(keywords: List[str]) -> List[str]:
    print("\n" + "="*60)
    print("🔑 请确认搜索关键词")
    print("="*60)
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw}")
    print("\n选项:")
    print("  [Enter] 使用当前关键词继续")
    print("  [e] 编辑关键词（输入新的关键词，用逗号分隔）")
    print("  [q] 退出")
    choice = input("\n请选择 [Enter/e/q]: ").strip().lower()
    if choice == 'q':
        print("用户取消")
        exit(0)
    elif choice == 'e':
        new_keywords = input("请输入新的关键词（用逗号分隔）: ").strip()
        if new_keywords:
            keywords = [kw.strip() for kw in new_keywords.split(",") if kw.strip()]
            print(f"✅ 更新关键词: {keywords}")
    return keywords


def interactive_confirm_prompt(prompt_type: str, prompt: str) -> str:
    print("\n" + "="*60)
    print(f"📝 请确认{prompt_type} Prompt")
    print("="*60)
    # 限制显示长度防止刷屏，但传给 LLM 的依然是完整的 prompt
    print(prompt[:600] + "..." if len(prompt) > 600 else prompt)
    print("\n选项:")
    print("  [Enter] 使用当前 Prompt 继续")
    print("  [e] 编辑 Prompt")
    print("  [q] 退出")
    choice = input("\n请选择 [Enter/e/q]: ").strip().lower()
    if choice == 'q':
        print("用户取消")
        exit(0)
    elif choice == 'e':
        print("请输入新的 Prompt（输入空行结束）:")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        if lines:
            prompt = "\n".join(lines)
            print(f"✅ Prompt 已更新")
    return prompt


def interactive_confirm_crawl_result(paper_count: int) -> bool:
    print("\n" + "="*60)
    print(f"📊 共爬取 {paper_count} 篇论文")
    print("="*60)
    print("选项:")
    print("  [Enter] 继续进行 LLM 筛选")
    print("  [q] 退出（保留已爬取的数据）")
    choice = input("\n请选择 [Enter/q]: ").strip().lower()
    return choice != 'q'


def deduplicate_papers(papers: List[PaperData]) -> List[PaperData]:
    seen_titles = set()
    unique_papers = []
    for paper in papers:
        normalized_title = ' '.join(paper.title.lower().strip().split())
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_papers.append(paper)
    return unique_papers


def crawl_papers(config: Config, keywords: List[str]) -> List[PaperData]:
    all_papers = []
    print("\n" + "="*60)
    print("📚 步骤 2/4: 爬取论文")
    print("="*60)
    print(f"🔑 使用关键词: {', '.join(keywords)}")
    openreview_supported = {'ICLR', 'ICML', 'NEURIPS', 'NIPS', 'ACL', 'TRL', 'TMLR'}
    
    for year in config.years:
        or_crawler = OpenReviewCrawler(year)
        oa_crawler = OpenAlexCrawler(email=config.openalex_email, min_citations=5) 
        
        for conf in config.conferences:
            conf_upper = conf.upper()
            print(f"\n--- {conf_upper} {year} ---")
            if conf_upper in openreview_supported:
                papers = or_crawler.crawl(conf_upper, keywords=keywords)
            else:
                papers = oa_crawler.crawl(conf_upper, year, keywords=keywords)
            all_papers.extend(papers)
            
    if config.crawl_arxiv and keywords:
        print(f"\n--- Arxiv ---")
        arxiv_crawler = ArxivCrawler(min_citations=5)
        arxiv_years = list(range(min(config.years) - 1, max(config.years) + 1))
        papers = arxiv_crawler.crawl(
            keywords, 
            years=arxiv_years,
            max_results=config.arxiv_max_results,
            filter_by_keywords=True,
            filter_by_citations=True
        )
        all_papers.extend(papers)
        
    print(f"\n🔄 去重中...")
    before_dedup = len(all_papers)
    all_papers = deduplicate_papers(all_papers)
    if before_dedup > len(all_papers):
        print(f"   移除 {before_dedup - len(all_papers)} 篇重复论文")
    print(f"\n📊 总计: {len(all_papers)} 篇论文")
    write_csv(all_papers, config.raw_papers_path, include_filter_results=False)
    return all_papers


def run_pipeline(
    user_description: str,
    config: Optional[Config] = None,
    skip_crawl: bool = False,
    skip_filter: bool = False,
    html_only: bool = False,
    interactive: bool = True,
):
    if html_only:
        print("\n" + "="*60)
        print("📄 只生成 HTML 报告")
        print("="*60)
        write_html_from_csv(
            config.output_csv_path, 
            config.output_html_path,
            subtitle=f"基于: {user_description[:50]}..."
        )
        return
    
    print("\n" + "="*60)
    print("🚀 Paper Pipeline 启动")
    print("="*60)
    print(f"📅 年份: {config.years}")
    print(f"🎓 会议: {config.conferences}")
    print(f"📁 输出目录: {config.output_dir}")
    print(f"🔄 交互模式: {'开启' if interactive else '关闭'}")
    print(f"🧠 当前任务描述: {user_description[:80]}...")
    
    # ================== 备份实际使用的配置文件 ==================
    if hasattr(config, 'config_path') and os.path.exists(config.config_path):
        config_save_path = os.path.join(config.output_dir, f"used_{os.path.basename(config.config_path)}")
        try:
            shutil.copy2(config.config_path, config_save_path)
            print(f"💾 配置文件已备份至: {os.path.abspath(config_save_path)}")
        except Exception as e:
            print(f"⚠️ 配置文件备份失败: {e}")
    # ============================================================

    keywords = []
    filter_prompt = ""
    
    if not skip_crawl:
        print("\n" + "="*60)
        print("🧠 步骤 1/4: 生成关键词和筛选 Prompt")
        print("="*60)
        generated = generate_all(user_description, config.large_llm)
        keywords = generated["keywords"]
        filter_prompt = generated["fine_prompt"]
        if not keywords:
            print("❌ 未生成关键词，流程终止。请检查 API 配置。")
            return
        if interactive:
            keywords = interactive_confirm_keywords(keywords)
            
    elif not skip_filter:
        print("\n" + "="*60)
        print("🧠 步骤 1/4: 加载筛选 Prompt (跳过关键词生成)")
        print("="*60)
        try:
            raw_prompt = load_prompt_template("filter_template.txt")
            filter_prompt = raw_prompt.replace("{user_description}", user_description)
            print("   ✅ 已从本地加载 filter_template.txt 并注入任务描述")
        except Exception as e:
            print(f"❌ 读取 Prompt 失败: {e}")
            return

    if skip_crawl and os.path.exists(config.raw_papers_path):
        print("\n⏭️ 跳过爬取，加载已有数据...")
        df = pd.read_csv(config.raw_papers_path)
        papers = [PaperData.from_dict(row) for _, row in df.iterrows()]
        print(f"   加载了 {len(papers)} 篇论文")
    else:
        papers = crawl_papers(config, keywords)
    
    if not papers:
        print("❌ 未获取到论文，流程终止")
        return
    
    if interactive:
        if not interactive_confirm_crawl_result(len(papers)):
            print("✅ 数据已保存，流程终止")
            return
    
    if skip_filter:
        print("\n⏭️ 跳过筛选，直接生成 HTML...")
        filtered_papers = papers
    else:
        print("\n" + "="*60)
        print("🎯 步骤 3/4: DeepSeek 筛选")
        print("="*60)
        if interactive:
            filter_prompt = interactive_confirm_prompt("筛选", filter_prompt)
        
        # ================== 保存实际使用的 Prompt ==================
        prompt_save_path = os.path.join(config.output_dir, "used_filter_prompt.txt")
        try:
            with open(prompt_save_path, "w", encoding="utf-8") as f:
                f.write(filter_prompt)
            print(f"   💾 实际使用的 Prompt 已保存至: {os.path.abspath(prompt_save_path)}")
        except Exception as e:
            print(f"   ⚠️ Prompt 保存失败: {e}")
        # ============================================================

        llm_filter = FineFilter(config.large_llm, filter_prompt, concurrency=config.concurrency)
        filtered_papers = llm_filter.filter_papers(papers)
        if not filtered_papers:
            print("⚠️ 筛选后无论文通过")
            return
        write_csv(filtered_papers, config.output_csv_path, include_filter_results=True)
    
    print("\n" + "="*60)
    print("💾 步骤 4/4: 输出结果")
    print("="*60)
    write_html(
        filtered_papers, 
        config.output_html_path,
        subtitle=f"基于: {user_description[:50]}..."
    )
    print("\n" + "="*60)
    print("🎉 Pipeline 完成!")
    print("="*60)
    print(f"📊 统计:")
    print(f"   - 爬取论文: {len(papers)} 篇")
    print(f"   - 筛选通过: {len(filtered_papers)} 篇")
    print(f"\n📁 输出文件夹: {os.path.abspath(config.output_dir)}")
    print(f"   - 配置文件: used_{os.path.basename(config.config_path)}")
    print(f"   - 提示词: used_filter_prompt.txt")
    print(f"   - 报告: papers_report.html")


def main():
    parser = argparse.ArgumentParser(
        description="论文爬取与筛选 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                                # 完全使用默认 config 运行
  python main.py -d "强化学习新算法"            # 覆盖 config 中的描述
  python main.py --config configs/rl_config.py  # 指定其他配置文件
  python main.py --preview-prompts              # 仅预览 Prompt 并退出
  python main.py -d "..." --skip-crawl          # 跳过爬取
  python main.py -d "..." --skip-filter         # 跳过筛选
        """
    )
    
    parser.add_argument(
        "--config", 
        type=str, 
        default="configs/default_config.py", 
        help="配置文件路径 (默认: configs/default_config.py)"
    )
    
    parser.add_argument(
        "--preview-prompts", 
        action="store_true", 
        help="预览当前的 Prompt 模板内容并退出"
    )
    
    parser.add_argument(
        "--description", "-d",
        type=str,
        default=None,
        required=False,
        help="你的研究需求描述 (如果不在命令行提供，将从 config 读取)"
    )
    
    parser.add_argument(
        "--years", "-y",
        type=str,
        default=None,
        help="要爬取的年份，逗号分隔 (覆盖 config 设置)"
    )
    
    parser.add_argument(
        "--conferences", "-c",
        type=str,
        default=None,
        help="要爬取的会议，逗号分隔 (覆盖 config 设置)"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="输出目录 (覆盖 config 设置)"
    )
    
    parser.add_argument(
        "--no-arxiv",
        action="store_true",
        help="不爬取 Arxiv (覆盖 config 设置)"
    )
    
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="关闭交互模式"
    )
    
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="跳过爬取步骤，使用已有的原始数据"
    )
    
    parser.add_argument(
        "--skip-filter",
        action="store_true",
        help="跳过 LLM 筛选步骤"
    )
    
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="只从 CSV 生成 HTML（跳过爬取和筛选）"
    )
    
    args = parser.parse_args()
    
    if args.preview_prompts:
        preview_prompts()
        
    overrides = {}
    if args.description is not None:
        overrides['description'] = args.description.strip()
    if args.years is not None:
        overrides['years'] = [int(y.strip()) for y in args.years.split(",")]
    if args.conferences is not None:
        overrides['conferences'] = [c.strip().upper() for c in args.conferences.split(",")]
    if args.output_dir is not None:
        overrides['output_dir'] = args.output_dir
    if args.no_arxiv:
        overrides['crawl_arxiv'] = False
        
    config = load_config(config_path=args.config, **overrides)
    
    if not hasattr(config, 'description') or not config.description:
        if not args.html_only:
            parser.error("❌ 缺少研究描述！请在 config 文件中定义 DESCRIPTION，或使用 -d 参数传入。")
        else:
            config.description = "HTML Only Mode"
            
    run_pipeline(
        user_description=config.description,
        config=config,
        skip_crawl=args.skip_crawl,
        skip_filter=args.skip_filter,
        html_only=args.html_only,
        interactive=not args.no_interactive
    )

if __name__ == "__main__":
    main()