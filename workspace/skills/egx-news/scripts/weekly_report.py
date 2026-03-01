#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///
# -*- coding: utf-8 -*-
"""
weekly_report.py - إنشاء التقرير الأسبوعي للبورصة المصرية

الاستخدام:
    uv run weekly_report.py
    uv run weekly_report.py --no-send   # بدون إرسال Telegram
"""

import json
import sqlite3
import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# المسارات
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
SCRIPTS_DIR = Path(__file__).parent
config = None

def load_config():
    """تحميل الإعدادات"""
    global config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

def get_news_from_db(days=7):
    """جلب الأخبار من قاعدة البيانات"""
    db_path = config["database"]["path"]
    
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    c.execute("""SELECT date, title, content, source, symbol, pe_ratio, priority 
                 FROM news 
                 WHERE trusted=1 AND date >= ?
                 ORDER BY 
                    CASE priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    date DESC""", (cutoff,))
    
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

def get_statistics(news_list):
    """حساب إحصائيات الأسبوع"""
    stats = {
        "total_news": len(news_list),
        "high_priority": len([n for n in news_list if n["priority"] == "high"]),
        "medium_priority": len([n for n in news_list if n["priority"] == "medium"]),
        "low_priority": len([n for n in news_list if n["priority"] == "low"]),
        "sources": {},
        "symbols": {},
        "avg_pe": None
    }
    
    pe_values = [n["pe_ratio"] for n in news_list if n["pe_ratio"] is not None]
    if pe_values:
        stats["avg_pe"] = round(sum(pe_values) / len(pe_values), 2)
    
    for item in news_list:
        # إحصائيات المصادر
        source = item["source"]
        stats["sources"][source] = stats["sources"].get(source, 0) + 1
        
        # إحصائيات الأسهم
        symbol = item["symbol"]
        if symbol:
            stats["symbols"][symbol] = stats["symbols"].get(symbol, 0) + 1
    
    return stats

def generate_report_content(news_list, stats):
    """إنشاء محتوى التقرير الأسبوعي"""
    today = datetime.now()
    week_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")
    
    content = f"""# 📊 التقرير الأسبوعي للبورصة المصرية
**الفترة:** {week_start} إلى {week_end}
**المستثمر:** {config["investor"]["name"]}
**الاستراتيجية:** {config["investor"]["strategy"]}

---

## 📈 ملخص الأسبوع

| المؤشر | القيمة |
|--------|--------|
| إجمالي الأخبار الموثوقة | {stats["total_news"]} |
| أخبار عالية الأهمية | {stats["high_priority"]} |
| أخبار متوسطة الأهمية | {stats["medium_priority"]} |
| أخبار منخفضة الأهمية | {stats["low_priority"]} |
| متوسط مكرر الربحية | {stats["avg_pe"] if stats["avg_pe"] else "غير متاح"} |

---

## 🏆 أهم المصادر هذا الأسبوع

"""
    
    # ترتيب المصادر
    sorted_sources = sorted(stats["sources"].items(), key=lambda x: x[1], reverse=True)
    for source, count in sorted_sources[:5]:
        content += f"- **{source}:** {count} خبر\n"
    
    content += """
---

## 📰 أهم الأخبار

"""
    
    if news_list:
        # أخبار عالية الأهمية
        high_priority = [n for n in news_list if n["priority"] == "high"]
        if high_priority:
            content += "### 🔔 أخبار عاجلة\n\n"
            for item in high_priority[:5]:
                content += f"**{item['date'][:10]}** - {item['title']}\n"
                content += f"- المصدر: {item['source']}\n"
                content += f"- {item['content'][:150]}...\n\n"
        
        # أخبار متوسطة الأهمية
        medium_priority = [n for n in news_list if n["priority"] == "medium"]
        if medium_priority:
            content += "### 📋 أخبار متوسطة الأهمية\n\n"
            for item in medium_priority[:5]:
                pe_text = f" | PE: {item['pe_ratio']}" if item['pe_ratio'] else ""
                content += f"- {item['date'][:10]}: {item['title']} ({item['source']}{pe_text})\n"
        
        content += "\n"
    else:
        content += "_لا توجد أخبار موثوقة هذا الأسبوع._\n\n"
    
    content += f"""---

## 💼 حالة الأسهم المتابعة

| السهم | القطاع | عدد الأخبار | الحالة |
|-------|--------|-------------|--------|
| CIB | البنوك | {stats["symbols"].get("CIB", 0)} | متابعة |
| EGX30 | المؤشرات | {stats["symbols"].get("EGX30", 0)} | متابعة |
| الذهب | المعادن | {stats["symbols"].get("GOLD", 0)} | متابعة |

---

## 🎯 توصيات الأسبوع القادم

"""
    
    # توصيات بناءً على الأخبار
    if stats["high_priority"] > 0:
        content += "- ⚠️ **انتبه:** هناك أخبار عالية الأهمية تحتاج متابعة\n"
    
    if stats["avg_pe"] and stats["avg_pe"] < config["filters"]["pe_ratio_max"]:
        content += f"- ✅ **مكرر الربحية:** المتوسط ({stats['avg_pe']}) أقل من الحد الأقصى ({config['filters']['pe_ratio_max']})\n"
    
    content += f"""- 📅 تذكير: الاستثمار الشهري {config["investor"]["monthly_amount"]} جنيه
- 🎯 الأفق: {config["investor"]["time_horizon_years"]} سنوات

---

## 💰 التوزيع المقترح للاستثمار الشهري

| الأصل | النسبة | المبلغ |
|-------|--------|--------|
| CIB | 50% | {config["investor"]["monthly_amount"] * 0.5:.0f} جنيه |
| صندوق ذهب | 30% | {config["investor"]["monthly_amount"] * 0.3:.0f} جنيه |
| سيولة | 20% | {config["investor"]["monthly_amount"] * 0.2:.0f} جنيه |

---

## 📌 ملاحظات

1. جميع الأخبار في هذا التقرير **مرت بـ Double-Check**
2. المصادر المعتمدة: {", ".join(config["preferences"]["preferred_analysts"])}
3. تجاهل أي خبر من مصادر غير موثوقة

---

_تم إنشاء هذا التقرير تلقائياً بواسطة Egypt Stocks Skill_
_التاريخ: {today.strftime("%Y-%m-%d %H:%M")}_
"""
    
    return content

def save_report(content):
    """حفظ التقرير"""
    reports_dir = config["reports"]["path"]
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"weekly-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filepath

def send_telegram(message, file_path=None, priority="medium"):
    """إرسال إشعار Telegram"""
    cmd = ["uv", "run", str(SCRIPTS_DIR / "send_telegram.py")]
    
    if file_path:
        cmd.extend(["--file", file_path])
    
    cmd.extend(["--priority", priority])
    cmd.append(message)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout) if result.stdout else {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="إنشاء التقرير الأسبوعي")
    parser.add_argument("--no-send", action="store_true", help="بدون إرسال Telegram")
    args = parser.parse_args()
    
    load_config()
    
    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "report_type": "weekly"
    }
    
    # جلب الأخبار
    news_list = get_news_from_db(days=7)
    stats = get_statistics(news_list)
    
    output["statistics"] = stats
    
    # إنشاء التقرير
    report_content = generate_report_content(news_list, stats)
    report_path = save_report(report_content)
    output["report_path"] = report_path
    
    # ملخص
    today = datetime.now()
    week_start = (today - timedelta(days=7)).strftime("%m/%d")
    week_end = today.strftime("%m/%d")
    
    summary = f"📊 التقرير الأسبوعي ({week_start} - {week_end})\n"
    summary += f"📰 {stats['total_news']} خبر | 🔔 {stats['high_priority']} عاجل\n"
    
    if stats["avg_pe"]:
        summary += f"📈 متوسط PE: {stats['avg_pe']}\n"
    
    if news_list:
        high_news = [n for n in news_list if n["priority"] == "high"]
        if high_news:
            summary += f"⚡ أهم خبر: {high_news[0]['title'][:40]}..."
        else:
            summary += f"📋 أهم خبر: {news_list[0]['title'][:40]}..."
    
    output["summary"] = summary
    
    # إرسال Telegram
    if not args.no_send:
        telegram_result = send_telegram(summary, report_path, "medium")
        output["telegram"] = telegram_result
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
