#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///
# -*- coding: utf-8 -*-
"""
daily_report.py - إنشاء التقرير اليومي للبورصة المصرية

الاستخدام:
    uv run daily_report.py
    uv run daily_report.py --no-send   # بدون إرسال Telegram
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

def get_news_from_db(days=1):
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

def mark_news_processed(news_list):
    """تحديث حالة الأخبار إلى processed"""
    db_path = config["database"]["path"]
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    for item in news_list:
        c.execute("UPDATE news SET processed=1 WHERE title=?", (item["title"],))
    
    conn.commit()
    conn.close()

def generate_report_content(news_list):
    """إنشاء محتوى التقرير"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    content = f"""# 🏦 التقرير اليومي للبورصة المصرية
**التاريخ:** {today}
**المستثمر:** {config["investor"]["name"]}

---

## 📊 ملخص اليوم

- **عدد الأخبار الموثوقة:** {len(news_list)}
- **أخبار عالية الأهمية:** {len([n for n in news_list if n["priority"] == "high"])}
- **مكرر الربحية المستهدف:** ≤ {config["filters"]["pe_ratio_max"]}

---

## 📰 أخبار اليوم

"""
    
    if news_list:
        # أخبار عالية الأهمية
        high_priority = [n for n in news_list if n["priority"] == "high"]
        if high_priority:
            content += "### 🔔 أخبار عاجلة\n\n"
            for item in high_priority:
                content += f"- **{item['title']}**\n"
                content += f"  - المصدر: {item['source']}\n"
                content += f"  - {item['content'][:100]}...\n\n"
        
        # باقي الأخبار
        other_news = [n for n in news_list if n["priority"] != "high"]
        if other_news:
            content += "### 📋 أخبار أخرى\n\n"
            for item in other_news:
                pe_text = f" | PE: {item['pe_ratio']}" if item['pe_ratio'] else ""
                content += f"- {item['title']} ({item['source']}{pe_text})\n"
    else:
        content += "_لا توجد أخبار موثوقة جديدة اليوم._\n"
    
    content += f"""
---

## 📈 الأسهم المتابعة

| السهم | القطاع | الحالة |
|-------|--------|--------|
| CIB | البنوك | متابعة |
| EGX30 | المؤشرات | متابعة |
| الذهب | المعادن | متابعة |

---

## 💰 تذكير الاستثمار الشهري

- **المبلغ:** {config["investor"]["monthly_amount"]} جنيه
- **الاستراتيجية:** {config["investor"]["strategy"]}
- **أفق الاستثمار:** {config["investor"]["time_horizon_years"]} سنوات

---

_تم إنشاء هذا التقرير تلقائياً بواسطة Egypt Stocks Skill_
_جميع الأخبار مرت بـ Double-Check_
"""
    
    return content

def save_report(content):
    """حفظ التقرير"""
    reports_dir = config["reports"]["path"]
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"daily-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filepath

def send_telegram(message, file_path=None, priority="medium"):
    """إرسال إشعار Telegram باستخدام send_telegram.py"""
    cmd = ["uv", "run", str(SCRIPTS_DIR / "send_telegram.py"),"--summarize-llm"]
    
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
    parser = argparse.ArgumentParser(description="إنشاء التقرير اليومي")
    parser.add_argument("--no-send", action="store_true", help="بدون إرسال Telegram")
    args = parser.parse_args()
    
    load_config()
    
    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "report_type": "daily"
    }
    
    # جلب الأخبار
    news_list = get_news_from_db(days=1)
    output["news_count"] = len(news_list)
    output["high_priority_count"] = len([n for n in news_list if n["priority"] == "high"])
    
    # إنشاء التقرير
    report_content = generate_report_content(news_list)
    report_path = save_report(report_content)
    output["report_path"] = report_path
    
    # ملخص
    if news_list:
        high_news = [n for n in news_list if n["priority"] == "high"]
        summary = f"📊 تقرير {datetime.now().strftime('%Y-%m-%d')}\n"
        summary += f"عدد الأخبار: {len(news_list)} | عاجل: {len(high_news)}\n"
        if high_news:
            summary += f"🔔 {high_news[0]['title'][:50]}..."
        else:
            summary += f"أهمها: {news_list[0]['title'][:50]}..."
    else:
        summary = f"📊 تقرير {datetime.now().strftime('%Y-%m-%d')}\nلا توجد أخبار موثوقة جديدة."
    
    output["summary"] = summary
    
    # إرسال Telegram
    if not args.no_send:
        priority = "high" if output["high_priority_count"] > 0 else "medium"
        telegram_result = send_telegram(summary, report_path, priority)
        output["telegram"] = telegram_result
    
    # تحديث حالة الأخبار
    mark_news_processed(news_list)
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
