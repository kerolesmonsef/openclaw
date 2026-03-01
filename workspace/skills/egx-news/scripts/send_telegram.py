#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "openai",
# ]
# ///
# -*- coding: utf-8 -*-
"""
send_telegram.py - إرسال إشعارات Telegram مع تلخيص ذكي

الاستخدام:
    uv run send_telegram.py "الرسالة هنا"
    uv run send_telegram.py --file /path/to/report.md "ملخص الرسالة"
    uv run send_telegram.py --file /path/to/report.md --summarize        # تلخيص تلقائي (regex)
    uv run send_telegram.py --file /path/to/report.md --summarize-llm    # تلخيص بالذكاء الاصطناعي
    uv run send_telegram.py --file /path/to/report.md --summarize-llm --provider chatanywhere
"""

import json
import argparse
import sys
import requests
import re
from datetime import datetime
from pathlib import Path

# استيراد خدمة LLM
from llm_service import summarize_report_file

# المسارات
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
config = None

def load_config():
    """تحميل الإعدادات"""
    global config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

def summarize_report(file_path):
    """
    تلخيص ذكي للتقرير
    يستخرج أهم النقاط من ملف Markdown
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        summary_parts = []
        
        # استخراج التاريخ
        date_match = re.search(r'\*\*التاريخ:\*\*\s*(.+)', content)
        if date_match:
            summary_parts.append(f"📅 {date_match.group(1)}")
        
        # استخراج عدد الأخبار
        news_count = re.search(r'\*\*عدد الأخبار الموثوقة:\*\*\s*(\d+)', content)
        high_count = re.search(r'\*\*أخبار عالية الأهمية:\*\*\s*(\d+)', content)
        
        if news_count:
            count_text = f"📊 {news_count.group(1)} خبر موثق"
            if high_count and int(high_count.group(1)) > 0:
                count_text += f" | 🔔 {high_count.group(1)} عاجل"
            summary_parts.append(count_text)
        
        # استخراج الأخبار العاجلة (أول 3)
        urgent_section = re.search(r'### 🔔 أخبار عاجلة\n\n(.*?)(?=###|---)', content, re.DOTALL)
        if urgent_section:
            urgent_news = re.findall(r'- \*\*(.+?)\*\*', urgent_section.group(1))
            if urgent_news:
                summary_parts.append("\n🔴 أخبار عاجلة:")
                for news in urgent_news[:3]:
                    summary_parts.append(f"  • {news[:60]}...")
        
        # استخراج أهم الأخبار العادية (أول 3)
        other_section = re.search(r'### 📋 أخبار أخرى\n\n(.*?)(?=---|##)', content, re.DOTALL)
        if other_section:
            other_news = re.findall(r'- (.+?) \(', other_section.group(1))
            if other_news:
                summary_parts.append("\n📰 أهم الأخبار:")
                for news in other_news[:3]:
                    summary_parts.append(f"  • {news[:50]}...")
        
        # إحصائيات المصادر (للتقرير الأسبوعي)
        sources_section = re.search(r'### 📰 أهم المصادر\n\n(.*?)(?=###|---)', content, re.DOTALL)
        if sources_section:
            sources = re.findall(r'\| (.+?) \| (\d+) \|', sources_section.group(1))
            if sources:
                top_sources = sorted(sources, key=lambda x: int(x[1]), reverse=True)[:3]
                summary_parts.append("\n📰 أهم المصادر:")
                for source, count in top_sources:
                    summary_parts.append(f"  • {source}: {count}")
        
        # إحصائيات الأسهم (للتقرير الأسبوعي)
        symbols_section = re.search(r'### 📈 أكثر الأسهم ذكراً\n\n(.*?)(?=###|---)', content, re.DOTALL)
        if symbols_section:
            symbols = re.findall(r'\| (.+?) \| (\d+) \|', symbols_section.group(1))
            if symbols:
                top_symbols = sorted(symbols, key=lambda x: int(x[1]), reverse=True)[:3]
                summary_parts.append("\n📈 أكثر الأسهم تداولاً:")
                for symbol, count in top_symbols:
                    summary_parts.append(f"  • {symbol}: {count} ذكر")
        
        # تذكير الاستثمار
        monthly = re.search(r'\*\*المبلغ:\*\*\s*(.+)', content)
        if monthly:
            summary_parts.append(f"\n💰 تذكير: {monthly.group(1)}")
        
        if summary_parts:
            return "\n".join(summary_parts)
        else:
            return "📊 تقرير البورصة المصرية - اضغط على الملف للتفاصيل"
            
    except Exception as e:
        return f"📊 تقرير البورصة المصرية (خطأ في التلخيص: {str(e)[:30]})"

def send_message(text, parse_mode="Markdown"):
    """إرسال رسالة نصية"""
    bot_token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    try:
        r = requests.post(url, data=payload, timeout=30)
        r.raise_for_status()
        return {"status": "success", "message_id": r.json().get("result", {}).get("message_id")}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def send_document(file_path, caption=""):
    """إرسال ملف"""
    bot_token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]
    
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption}
            r = requests.post(url, data=data, files=files, timeout=60)
            r.raise_for_status()
        return {"status": "success", "file_sent": file_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="إرسال إشعارات Telegram مع تلخيص ذكي")
    parser.add_argument("message", type=str, nargs='?', default="", help="نص الرسالة")
    parser.add_argument("--file", type=str, help="مسار ملف للإرسال")
    parser.add_argument("--priority", type=str, choices=["high", "medium", "low"], default="medium", 
                        help="أولوية الرسالة")
    parser.add_argument("--summarize", action="store_true", help="تلخيص الملف تلقائياً (regex)")
    parser.add_argument("--summarize-llm", action="store_true", help="تلخيص الملف بالذكاء الاصطناعي")
    parser.add_argument("--provider", type=str, help="مزود LLM (openrouter, chatanywhere)")
    parser.add_argument("--model", type=str, help="نموذج LLM المستخدم")
    parser.add_argument("--max-length", type=int, default=100, help="الحد الأقصى لطول التلخيص بالكلمات")
    args = parser.parse_args()
    
    load_config()
    
    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "results": []
    }
    
    # تحديد الرسالة
    if args.summarize_llm and args.file:
        # تلخيص بالذكاء الاصطناعي
        message = summarize_report_file(
            args.file,
            provider=args.provider,
            model=args.model,
            max_length=args.max_length
        )
        output["summarized"] = True
        output["summarize_method"] = "llm"
        output["provider"] = args.provider or config.get("llm", {}).get("default_provider", "openrouter")
    elif args.summarize and args.file:
        # تلخيص تلقائي للملف (regex)
        message = summarize_report(args.file)
        output["summarized"] = True
        output["summarize_method"] = "regex"
    elif args.message:
        message = args.message
    else:
        message = "📊 تقرير البورصة المصرية"
    
    # تنسيق الرسالة حسب الأولوية
    if args.priority == "high":
        formatted_message = f"🔔 *تنبيه فوري*\n\n{message}"
    elif args.priority == "medium":
        formatted_message = f"📊 *تحديث*\n\n{message}"
    else:
        formatted_message = message
    
    # إرسال الرسالة
    msg_result = send_message(formatted_message)
    output["results"].append({"type": "message", **msg_result})
    output["message_sent"] = message[:100] + "..." if len(message) > 100 else message
    
    # إرسال الملف (إن وجد)
    if args.file:
        caption = message[:50] + "..." if len(message) > 50 else message
        file_result = send_document(args.file, f"📄 {caption}")
        output["results"].append({"type": "document", **file_result})
    
    # تحديث الـ status الإجمالي
    if any(r.get("status") == "error" for r in output["results"]):
        output["status"] = "partial_error"
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
