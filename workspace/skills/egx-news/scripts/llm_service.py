#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai",
# ]
# ///
# -*- coding: utf-8 -*-
"""
llm_service.py - خدمة الذكاء الاصطناعي للتلخيص

الاستخدام:
    from llm_service import summarize
    
    # تلخيص نص
    summary = summarize("نص طويل هنا...")
    
    # تلخيص مع خيارات
    summary = summarize(text, max_length=200, provider="chatanywhere", model="gpt-4o-ca")
"""

import json
from pathlib import Path
from openai import OpenAI

# المسارات
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

_config = None


def _load_config():
    """تحميل الإعدادات"""
    global _config
    if _config is None:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config = json.load(f)
    return _config


def get_llm_config():
    """الحصول على إعدادات LLM"""
    config = _load_config()
    return config.get("llm", {})


def get_provider_config(provider: str = None):
    """الحصول على إعدادات مزود معين"""
    llm_config = get_llm_config()
    if provider is None:
        provider = llm_config.get("default_provider", "openrouter")
    
    providers = llm_config.get("providers", {})
    return providers.get(provider, {})


def get_openai_client(provider: str = None):
    """إنشاء عميل OpenAI بناءً على المزود"""
    provider_config = get_provider_config(provider)
    
    return OpenAI(
        api_key=provider_config.get("api_key", ""),
        base_url=provider_config.get("api_url", "https://openrouter.ai/api/v1"),
        default_headers={
            "HTTP-Referer": "https://egx-news.local",
            "X-Title": "EGX News Summarizer",
        }
    )


def summarize(
    text: str,
    max_length: int = None,
    provider: str = None,
    model: str = None,
    temperature: float = None,
    system_prompt: str = None,
    language: str = "ar"
) -> str:
    """
    تلخيص نص طويل باستخدام LLM
    
    Args:
        text: النص المراد تلخيصه
        max_length: الحد الأقصى لطول الملخص (بالكلمات تقريباً)
        provider: مزود LLM (openrouter, chatanywhere)
        model: اسم النموذج
        temperature: درجة الإبداعية (0.0 - 1.0)
        system_prompt: رسالة النظام المخصصة
        language: لغة الملخص (ar, en)
    
    Returns:
        النص الملخص
    """
    if not text or not text.strip():
        return ""
    
    # تحميل الإعدادات
    llm_config = get_llm_config()
    summarize_config = llm_config.get("summarize", {})
    
    # تحديد المزود
    if provider is None:
        provider = llm_config.get("default_provider", "openrouter")
    
    provider_config = get_provider_config(provider)
    
    # تحديد النموذج
    if model is None:
        model = provider_config.get("default_model", "meta-llama/llama-3.3-70b-instruct:free")
    
    # تحديد الإعدادات
    if temperature is None:
        temperature = summarize_config.get("temperature", 0.3)
    
    max_tokens = summarize_config.get("max_tokens", 500)
    
    # تحديد system_prompt
    if system_prompt is None:
        if language == "ar":
            system_prompt = summarize_config.get(
                "system_prompt",
                "أنت مساعد متخصص في تلخيص أخبار البورصة المصرية. قم بتلخيص الأخبار بشكل موجز ومفيد للمستثمر. استخدم العربية الفصحى."
            )
        else:
            system_prompt = "You are an expert financial news summarizer. Summarize the news concisely and helpfully for investors."
    
    # بناء الـ prompt
    if max_length:
        if language == "ar":
            user_prompt = f"قم بتلخيص النص التالي في حدود {max_length} كلمة تقريباً:\n\n{text}"
        else:
            user_prompt = f"Summarize the following text in approximately {max_length} words:\n\n{text}"
    else:
        if language == "ar":
            user_prompt = f"قم بتلخيص النص التالي بشكل موجز:\n\n{text}"
        else:
            user_prompt = f"Summarize the following text concisely:\n\n{text}"
    
    try:
        client = get_openai_client(provider)
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return completion.choices[0].message.content.strip()
        
    except Exception as e:
        # في حالة الخطأ، نعيد رسالة خطأ واضحة
        return f"[خطأ في التلخيص: {str(e)[:50]}]"


def summarize_news_list(
    news_items: list,
    max_items: int = 5,
    provider: str = None,
    model: str = None
) -> str:
    """
    تلخيص قائمة أخبار
    
    Args:
        news_items: قائمة الأخبار (كل خبر dict يحتوي على title, content, source)
        max_items: أقصى عدد أخبار للتلخيص
        provider: مزود LLM
        model: اسم النموذج
    
    Returns:
        تلخيص موحد للأخبار
    """
    if not news_items:
        return "لا توجد أخبار للتلخيص"
    
    # تحضير النص
    news_text = ""
    for i, item in enumerate(news_items[:max_items], 1):
        title = item.get("title", "")
        content = item.get("content", item.get("summary", ""))
        source = item.get("source", "")
        
        news_text += f"{i}. {title}"
        if content:
            news_text += f"\n   {content[:200]}..."
        if source:
            news_text += f"\n   (المصدر: {source})"
        news_text += "\n\n"
    
    system_prompt = """أنت محلل مالي متخصص في البورصة المصرية.
قم بتلخيص الأخبار التالية في نقاط موجزة:
- استخرج أهم المعلومات للمستثمر
- اذكر الأسهم المذكورة
- حدد الأخبار الإيجابية والسلبية
- استخدم العربية الفصحى"""
    
    return summarize(
        news_text,
        max_length=150,
        provider=provider,
        model=model,
        system_prompt=system_prompt
    )


def summarize_report_file(
    file_path: str,
    provider: str = None,
    model: str = None,
    max_length: int = 100
) -> str:
    """
    تلخيص ملف تقرير
    
    Args:
        file_path: مسار الملف
        provider: مزود LLM
        model: اسم النموذج
        max_length: الحد الأقصى لطول الملخص
    
    Returns:
        تلخيص التقرير
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # إزالة الـ Markdown formatting الزائد
        # content = content.replace("###", "").replace("**", "").replace("*", "")
        
        system_prompt = """أنت محلل مالي متخصص. قم بتلخيص تقرير البورصة المصرية التالي:
- استخرج أهم الأخبار (العاجلة أولاً)
- اذكر الأرقام المهمة
- حدد الأسهم الأكثر ذكراً
- اكتب التلخيص بصيغة نقاط مختصرة
- استخدم الإيموجي المناسبة (📈📉🔔💰)"""
        
        return summarize(
            content,
            max_length=max_length,
            provider=provider,
            model=model,
            system_prompt=system_prompt
        )
        
    except Exception as e:
        return f"[خطأ في قراءة الملف: {str(e)[:50]}]"


# للاختبار المباشر
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="تلخيص النصوص باستخدام LLM")
    parser.add_argument("text", type=str, nargs='?', default="", help="النص المراد تلخيصه")
    parser.add_argument("--file", type=str, help="مسار ملف للتلخيص")
    parser.add_argument("--provider", type=str, help="مزود LLM (openrouter, chatanywhere)")
    parser.add_argument("--model", type=str, help="اسم النموذج")
    parser.add_argument("--max-length", type=int, default=100, help="الحد الأقصى لطول الملخص")
    args = parser.parse_args()
    
    if args.file:
        result = summarize_report_file(
            args.file,
            provider=args.provider,
            model=args.model,
            max_length=args.max_length
        )
    elif args.text:
        result = summarize(
            args.text,
            max_length=args.max_length,
            provider=args.provider,
            model=args.model
        )
    else:
        print("الرجاء إدخال نص أو ملف للتلخيص")
        print("Usage: uv run llm_service.py 'نص للتلخيص'")
        print("       uv run llm_service.py --file /path/to/report.md")
        exit(1)
    
    print(result)
