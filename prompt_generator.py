"""
Prompt 自动生成器 - 根据用户需求描述生成关键词和筛选 prompt
"""
import os
import re
from typing import Dict, List
from config import LLMConfig
from filters.base import SiliconFlowClient


def load_prompt_template(file_name: str) -> str:
    """从本地文件加载 prompt 模板"""
    path = os.path.join("prompts", file_name)
    
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"❌ 找不到 Prompt 文件: {path}。\n"
            f"请确保 'prompts' 文件夹存在，且包含 '{file_name}' 文件。"
        )
        
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def generate_all(user_description: str, llm_config: LLMConfig) -> Dict:
    """
    根据用户需求描述，调用大模型生成关键词和筛选 prompt
    """
    print("\n🧠 正在根据您的需求生成关键词和筛选 Prompt...")
    
    try:
        # 1. 动态加载 generator_template
        generator_template = load_prompt_template("generator_template.txt")
    except FileNotFoundError as e:
        print(e)
        return get_defaults()
    
    client = SiliconFlowClient(llm_config)
    prompt = generator_template.format(user_description=user_description)
    
    response = client.call(
        prompt, 
        system_prompt="你是一个专业的 AI 研究助手，擅长理解用户需求并生成高质量的搜索关键词和筛选 prompt。"
    )
    
    if not response:
        print("   ❌ 生成失败，将使用默认配置")
        return get_defaults()
    
    # 解析响应
    keywords = extract_keywords(response)
    filter_prompt = extract_tag(response, "prompt")
    
    # 验证和补充
    if not keywords:
        print("   ⚠️ 关键词生成失败，请手动指定")
        keywords = []
    
    if not filter_prompt:
        print("   ⚠️ Prompt 解析失败，将使用默认模板")
        filter_prompt = get_defaults().get("fine_prompt", "")
    
    # 打印结果
    print("   ✅ 生成完成")
    print("\n" + "="*60)
    print("🔑 生成的搜索关键词:")
    print("-"*60)
    for i, kw in enumerate(keywords, 1):
        print(f"   {i}. {kw}")
    print("\n" + "="*60)
    print("📝 生成的筛选 Prompt:")
    print("-"*60)
    print(filter_prompt[:500] + "..." if len(filter_prompt) > 500 else filter_prompt)
    print("="*60 + "\n")
    
    return {
        "keywords": keywords,
        "fine_prompt": filter_prompt,
        "coarse_prompt": filter_prompt
    }


def extract_tag(text: str, tag: str) -> str:
    """提取 XML 标签内容"""
    pattern = rf'<{tag}>\s*(.*?)\s*</{tag}>'
    match = re.search(pattern, text, re.S | re.I)
    if match:
        return match.group(1).strip()
    return ""


def extract_keywords(text: str) -> List[str]:
    """提取关键词列表"""
    keywords_text = extract_tag(text, "keywords")
    if not keywords_text:
        return []
    
    keywords = re.split(r'[,，、\n]+', keywords_text)
    keywords = [kw.strip() for kw in keywords if kw.strip()]
    return keywords[:8]


def get_defaults() -> Dict:
    """获取默认配置，直接从 filter_template.txt 加载"""
    try:
        default_fine = load_prompt_template("filter_template.txt")
    except FileNotFoundError as e:
        print(f"⚠️ {e}")
        default_fine = "⚠️ 未能加载默认筛选 Prompt，请确保 prompts/filter_template.txt 存在。"
        
    return {
        "keywords": [],
        "fine_prompt": default_fine,
        "coarse_prompt": default_fine
    }