#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "beautifulsoup4",
# ]
# ///
# -*- coding: utf-8 -*-
"""
fetch_news.py - جلب أخبار البورصة المصرية مع Double-Check

الاستخدام:
    uv run fetch_news.py              # أخبار اليوم
    uv run fetch_news.py --days 7     # أخبار آخر 7 أيام
    uv run fetch_news.py --symbol CIB # أخبار سهم معين
    uv run fetch_news.py --raw        # جلب الأخبار الخام للـ LLM
    
مصادر مجانية:
    - Google News RSS (البورصة المصرية)
    - Google Finance RSS
"""

import json
import sqlite3
import argparse
import sys
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

# المسارات
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
DB_PATH = None
config = None

def load_config():
    """تحميل الإعدادات"""
    global config, DB_PATH
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    DB_PATH = config["database"]["path"]

def init_db():
    """إنشاء قاعدة البيانات"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  title TEXT,
                  content TEXT,
                  source TEXT,
                  symbol TEXT,
                  pe_ratio REAL,
                  trusted INTEGER DEFAULT 0,
                  priority TEXT,
                  processed INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def is_source_trusted(source):
    """التحقق من موثوقية المصدر"""
    preferred = config["preferences"]["preferred_analysts"]
    blacklist = config["preferences"]["blacklist_sources"]
    trusted_sources = config["preferences"].get("trusted_news_sources", [])
    
    source_lower = source.lower()
    
    # تحقق من القائمة السوداء
    if any(bad in source_lower for bad in blacklist):
        return False
    
    # تحقق من المحللين المفضلين
    if source in preferred:
        return True
    
    # تحقق من قائمة المصادر الموثوقة الجديدة
    for trusted in trusted_sources:
        if trusted.lower() in source_lower or source_lower in trusted.lower():
            return True
    
    # مصادر إضافية معروفة
    known_sources = ["investing", "cnbc", "mubasher", "faros", "hc", "morgan", 
                     "bloomberg", "reuters", "الأهرام", "المال", "مباشر"]
    if any(src in source_lower for src in known_sources):
        return True
    
    return False

def has_long_term_keywords(text):
    """التحقق من وجود كلمات طويل الأجل"""
    keywords = config["filters"]["long_term_keywords"]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

def pe_ratio_ok(pe):
    """التحقق من مكرر الربحية"""
    if pe is None:
        return True
    return pe <= config["filters"]["pe_ratio_max"]

def double_check_news(title, content, source, pe_ratio):
    """
    Double-Check للخبر
    يرجع: (passed, reason)
    """
    # 1. المصدر موثوق؟
    if not is_source_trusted(source):
        return False, f"مصدر غير موثوق: {source}"
    
    # 2. كلمات طويل الأجل؟
    if config["filters"]["require_long_term_keywords"]:
        if not has_long_term_keywords(title + " " + content):
            return False, "لا يحتوي كلمات طويل الأجل"
    
    # 3. مكرر الربحية؟
    if not pe_ratio_ok(pe_ratio):
        return False, f"مكرر الربحية عالي: {pe_ratio}"
    
    return True, "passed"

def get_priority(title, content):
    """تحديد أولوية الخبر"""
    text = title + " " + content
    
    for priority, keywords in config["preferences"]["alert_priority"].items():
        if any(kw in text for kw in keywords):
            return priority
    
    return "low"

def store_news(title, content, source, symbol, pe_ratio, trusted, priority):
    """تخزين الخبر في قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # تحقق من عدم التكرار
    c.execute("SELECT id FROM news WHERE title=?", (title,))
    if c.fetchone():
        conn.close()
        return False  # موجود مسبقاً
    
    c.execute("""INSERT INTO news 
                 (date, title, content, source, symbol, pe_ratio, trusted, priority, processed) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
              (datetime.now().isoformat(), title, content, source, symbol, pe_ratio, trusted, priority))
    conn.commit()
    conn.close()
    return True

def get_news_from_db(days=1, symbol=None):
    """جلب الأخبار من قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    if symbol:
        c.execute("""SELECT date, title, content, source, symbol, pe_ratio, priority 
                     FROM news 
                     WHERE trusted=1 AND date >= ? AND symbol LIKE ?
                     ORDER BY date DESC""", (cutoff, f"%{symbol}%"))
    else:
        c.execute("""SELECT date, title, content, source, symbol, pe_ratio, priority 
                     FROM news 
                     WHERE trusted=1 AND date >= ?
                     ORDER BY date DESC""", (cutoff,))
    
    rows = c.fetchall()
    conn.close()
    
    return [{
        "date": row[0],
        "title": row[1],
        "content": row[2],
        "source": row[3],
        "symbol": row[4],
        "pe_ratio": row[5],
        "priority": row[6]
    } for row in rows]

# ============================================
# 🌐 جلب الأخبار من مصادر مجانية (Google News RSS)
# ============================================

def fetch_raw_news_from_google():
    """
    جلب الأخبار الخام من Google News RSS
    مجاني 100% - لا يحتاج API
    
    Returns:
        dict with 'raw_xml', 'parsed_items', 'source_url'
    """
    import requests
    
    # كلمات البحث للبورصة المصرية
    search_queries = [
        "البورصة المصرية",
        "EGX stocks",
        "CIB Egypt bank",
        "Egyptian stock market"
    ]
    
    all_items = []
    raw_data = []
    
    for query in search_queries:
        try:
            # Google News RSS URL
            encoded_query = quote(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ar&gl=EG&ceid=EG:ar"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                raw_data.append({
                    'query': query,
                    'url': url,
                    'xml': response.text[:5000]  # أول 5000 حرف
                })
                
                # محاولة parse بسيط للـ XML
                items = parse_rss_simple(response.text)
                all_items.extend(items)
                
        except Exception as e:
            print(f"⚠️ Error fetching {query}: {e}", file=sys.stderr)
    
    return {
        'raw_data': raw_data,
        'parsed_items': all_items,
        'count': len(all_items),
        'timestamp': datetime.now().isoformat()
    }

def parse_rss_simple(xml_text):
    """
    Parse بسيط للـ RSS - يستخرج العناوين والروابط
    """
    items = []
    try:
        # إزالة namespaces للتسهيل
        xml_clean = re.sub(r'xmlns[^"]*"[^"]*"', '', xml_text)
        root = ET.fromstring(xml_clean)
        
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubdate_elem = item.find('pubDate')
            source_elem = item.find('source')
            
            if title_elem is not None:
                items.append({
                    'title': title_elem.text or '',
                    'link': link_elem.text if link_elem is not None else '',
                    'pubDate': pubdate_elem.text if pubdate_elem is not None else '',
                    'source': source_elem.text if source_elem is not None else 'Google News'
                })
    except ET.ParseError as e:
        print(f"⚠️ XML Parse Error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ Error: {e}", file=sys.stderr)
    
    return items

def fetch_news_for_llm():
    """
    جلب الأخبار الخام لتمريرها للـ LLM
    الـ LLM هيحولها لـ JSON منسق
    
    Returns:
        str: نص الأخبار الخام للـ LLM
    """
    result = fetch_raw_news_from_google()
    
    # تجهيز النص للـ LLM
    llm_prompt = f"""
أنت محلل أخبار البورصة المصرية. حول الأخبار التالية إلى JSON:

## الأخبار الخام ({result['count']} خبر):
"""
    
    for i, item in enumerate(result['parsed_items'][:20], 1):  # أول 20 خبر
        llm_prompt += f"""
{i}. العنوان: {item['title']}
   المصدر: {item['source']}
   التاريخ: {item['pubDate']}
"""
    
    llm_prompt += """

## المطلوب:
حول كل خبر إلى JSON بالشكل التالي:
{
    "title": "العنوان",
    "content": "ملخص من العنوان",
    "source": "مصدر الخبر",
    "symbol": "رمز السهم إن وجد (CIB, EGX30, GOLD, etc.) أو فارغ",
    "pe_ratio": null,
    "is_relevant": true/false (هل متعلق بالبورصة المصرية؟)
}

أرجع JSON array فقط بدون أي نص إضافي.
"""
    
    return {
        'prompt_for_llm': llm_prompt,
        'raw_items': result['parsed_items'],
        'raw_data': result['raw_data'],
        'timestamp': result['timestamp']
    }

def convert_raw_to_news(parsed_items):
    """
    تحويل الأخبار المجلوبة من RSS إلى الشكل المطلوب
    """
    news = []
    for item in parsed_items:
        # استنتاج الرمز من العنوان
        symbol = detect_symbol(item['title'])
        
        news.append({
            'title': item['title'],
            'content': item['title'],  # نفس العنوان كمحتوى مبدئي
            'source': item['source'],
            'symbol': symbol,
            'pe_ratio': None
        })
    return news

def detect_symbol(text):
    """اكتشاف رمز السهم من النص"""
    text_upper = text.upper()
    
    symbols_map = {
        'CIB': ['CIB', 'التجاري الدولي', 'البنك التجاري'],
        'QNBA': ['QNB', 'الأهلي القطري'],
        'COMI': ['COMI', 'كومي'],
        'EGX30': ['EGX30', 'EGX 30', 'المؤشر الرئيسي', 'البورصة المصرية'],
        'GOLD': ['GOLD', 'الذهب', 'ذهب'],
        'HRHO': ['طلعت مصطفى', 'HRHO'],
        'EAST': ['ايسترن'],
        'SWDY': ['السويدي', 'SWDY'],
    }
    
    for symbol, keywords in symbols_map.items():
        if any(kw in text_upper or kw in text for kw in keywords):
            return symbol
    
    return ''

def fetch_sample_news():
    """
    جلب أخبار تجريبية (يمكن استبدالها بـ web scraping حقيقي)
    """
    # TODO: استبدال بـ web scraping حقيقي من المصادر
    sample_news = [
        {
            "title": "CIB يحقق أرباحاً قياسية في الربع الرابع",
            "content": "البنك التجاري الدولي سجل صافي أرباح 5 مليار جنيه متجاوزاً التوقعات، المحللون يرون نمواً طويل الأجل.",
            "source": "HC",
            "symbol": "CIB",
            "pe_ratio": 9.5
        },
        {
            "title": "تراجع أسعار الذهب مع قوة الدولار",
            "content": "الذهب ينخفض 2% اليوم، لكن التوقعات إيجابية للمستثمرين طويلي الأجل. فرصة للاستثمار.",
            "source": "CNBC Arabic",
            "symbol": "GOLD",
            "pe_ratio": None
        },
        {
            "title": "توصية من Morgan Stanley بزيادة الوزن النسبي للأسهم المصرية",
            "content": "البنك يرى أن السوق ما زال رخيصاً وينصح بشراء CIB وEGX30. استثمار طويل الأجل.",
            "source": "Morgan Stanley",
            "symbol": "EGX30",
            "pe_ratio": 9.0
        },
        {
            "title": "شائعات على تويتر عن ارتفاع CIB",
            "content": "مصادر مجهولة تتوقع ارتفاع السهم 50% الأسبوع القادم!",
            "source": "twitter.com",
            "symbol": "CIB",
            "pe_ratio": None
        }
    ]
    return sample_news

def process_news(raw_news):
    """
    معالجة الأخبار مع Double-Check
    """
    results = {
        "processed": 0,
        "passed": 0,
        "rejected": 0,
        "high_priority": 0,
        "news": [],
        "rejected_news": []
    }
    
    for item in raw_news:
        title = item["title"]
        content = item["content"]
        source = item["source"]
        symbol = item.get("symbol", "")
        pe = item.get("pe_ratio")
        
        results["processed"] += 1
        
        # Double-Check
        passed, reason = double_check_news(title, content, source, pe)
        
        if passed:
            priority = get_priority(title, content)
            stored = store_news(title, content, source, symbol, pe, trusted=1, priority=priority)
            
            if stored:
                results["passed"] += 1
                if priority == "high":
                    results["high_priority"] += 1
                
                results["news"].append({
                    "title": title,
                    "source": source,
                    "symbol": symbol,
                    "priority": priority,
                    "pe_ratio": pe,
                    "double_check": "✅ passed"
                })
        else:
            results["rejected"] += 1
            results["rejected_news"].append({
                "title": title,
                "source": source,
                "reason": reason,
                "double_check": "❌ failed"
            })
    
    return results

def main():
    parser = argparse.ArgumentParser(description="جلب أخبار البورصة المصرية مع Double-Check")
    parser.add_argument("--days", type=int, default=1, help="عدد الأيام للبحث")
    parser.add_argument("--symbol", type=str, help="رمز السهم (CIB, EGX30, etc.)")
    parser.add_argument("--fetch", action="store_true", help="جلب أخبار جديدة")
    parser.add_argument("--live", action="store_true", help="جلب أخبار حية من Google News")
    parser.add_argument("--raw", action="store_true", help="طباعة الأخبار الخام للـ LLM")
    args = parser.parse_args()
    
    load_config()
    init_db()
    
    # 🔴 إذا طلب الأخبار الخام للـ LLM
    if args.raw:
        result = fetch_news_for_llm()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "days": args.days,
        "symbol": args.symbol
    }
    
    # جلب أخبار جديدة
    if args.live:
        # 🟢 جلب من Google News RSS (مجاني)
        raw_result = fetch_raw_news_from_google()
        raw_news = convert_raw_to_news(raw_result['parsed_items'])
        output["source"] = "Google News RSS (Live)"
        output["fetched_count"] = raw_result['count']
    else:
        # البيانات التجريبية
        raw_news = fetch_sample_news()
        output["source"] = "Sample Data"
    
    process_results = process_news(raw_news)
    output["fetch_results"] = process_results
    
    # جلب الأخبار من قاعدة البيانات
    db_news = get_news_from_db(days=args.days, symbol=args.symbol)
    output["news"] = db_news
    output["news_count"] = len(db_news)
    output["high_priority_count"] = len([n for n in db_news if n["priority"] == "high"])
    
    # ملخص
    if db_news:
        output["summary"] = f"عدد الأخبار الموثوقة: {len(db_news)}. " + \
                           f"أخبار عالية الأهمية: {output['high_priority_count']}. " + \
                           f"أهمها: {db_news[0]['title'][:50]}..."
    else:
        output["summary"] = "لا توجد أخبار موثوقة جديدة."
    
    # طباعة JSON
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
