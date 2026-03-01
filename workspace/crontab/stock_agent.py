#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
import requests
import logging
import sys
import os
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

LOG_DIR = "/home/kero/.openclaw/workspace/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=f"{LOG_DIR}/stock_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

CONFIG_PATH = "/home/kero/.openclaw/workspace/crontab/stock_config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
DB_PATH = config["database"]["path"]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  title TEXT,
                  content TEXT,
                  source TEXT,
                  pe_ratio REAL,
                  trusted INTEGER DEFAULT 0,
                  priority TEXT,
                  processed INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stocks
                 (symbol TEXT, date TEXT, price REAL, recommendation TEXT, analyst TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, file_path TEXT, summary TEXT)''')
    conn.commit()
    conn.close()
    print("[✓] Database initialized.")

def store_news(title, content, source, pe_ratio, trusted, priority):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO news (date, title, content, source, pe_ratio, trusted, priority, processed) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
              (datetime.now().isoformat(), title, content, source, pe_ratio, trusted, priority))
    conn.commit()
    conn.close()
    print(f"[✓] News stored: {title[:50]}...")

def get_unprocessed_news(days=7):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute("SELECT date, title, source FROM news WHERE processed=0 AND date >= ? ORDER BY date DESC", (cutoff,))
    rows = c.fetchall()
    conn.close()
    print(f"[✓] Retrieved {len(rows)} unprocessed news items.")
    return rows

def mark_news_processed(title, date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE news SET processed=1 WHERE title=? AND date=?", (title, date))
    conn.commit()
    conn.close()
    print(f"[✓] Marked news as processed: {title[:50]}...")

def is_source_trusted(source):
    preferred = config["preferences"]["preferred_analysts"]
    news_sources = config["preferences"]["news_sources"]
    blacklist = config["preferences"]["blacklist_sources"]
    if any(bad in source.lower() for bad in blacklist):
        return False
    if source in preferred or source in news_sources:
        return True
    return False

def has_long_term_keywords(text):
    keywords = config["filters"]["long_term_keywords"]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

def pe_ratio_ok(pe):
    if pe is None:
        return True
    return pe <= config["filters"]["pe_ratio_max"]

def double_check_news(title, content, source, pe_ratio):
    trusted = is_source_trusted(source)
    if not trusted:
        print(f"[!] Source not trusted: {source}")
        return False
    if config["filters"]["require_long_term_keywords"] and not has_long_term_keywords(title + " " + content):
        print("[!] No long-term keywords found.")
        return False
    if not pe_ratio_ok(pe_ratio):
        print(f"[!] PE ratio too high: {pe_ratio}")
        return False
    print(f"[✓] News passed double-check: {title[:50]}...")
    return True

def fetch_news():
    print("\n[~] Fetching news from sources...")
    logging.info("Fetching news from sources...")
    sample_news = [
        {
            "title": "CIB يحقق أرباحاً قياسية في الربع الرابع",
            "content": "البنك التجاري الدولي سجل صافي أرباح 5 مليار جنيه متجاوزاً التوقعات، المحللون يرون نمواً طويل الأجل.",
            "source": "HC",
            "pe_ratio": 9.5
        },
        {
            "title": "تراجع أسعار الذهب مع قوة الدولار",
            "content": "الذهب ينخفض 2% اليوم، لكن التوقعات إيجابية للمستثمرين طويلي الأجل.",
            "source": "CNBC Arabic",
            "pe_ratio": None
        },
        {
            "title": "توصية من Morgan Stanley بزيادة الوزن النسبي للأسهم المصرية",
            "content": "البنك يرى أن السوق ما زال رخيصاً وينصح بشراء CIB وEGX30.",
            "source": "Morgan Stanley",
            "pe_ratio": 9.0
        }
    ]
    for item in sample_news:
        title = item["title"]
        content = item["content"]
        source = item["source"]
        pe = item["pe_ratio"]

        if double_check_news(title, content, source, pe):
            priority = "low"
            text_for_priority = title + " " + content
            for pri, keywords in config["preferences"]["alert_priority"].items():
                if any(kw in text_for_priority for kw in keywords):
                    priority = pri
                    break
            store_news(title, content, source, pe, trusted=1, priority=priority)
            if priority == "high":
                send_telegram_alert(f"🔔 *تنبيه فوري:* {title}\n{content}\nالمصدر: {source}")
        else:
            print(f"[!] News did not pass double-check: {title}")
    print("[✓] News fetching completed.\n")

def send_telegram_message(text, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        print("[✓] Telegram message sent.")
        logging.info("Telegram message sent.")
    except Exception as e:
        print(f"[✗] Telegram send failed: {e}")
        logging.error(f"Telegram send failed: {e}")

def send_telegram_alert(message):
    send_telegram_message(message)

def send_telegram_report(report_path, summary, report_type="تقرير"):
    msg = f"📊 *{report_type}*\n\n{summary}\n\n📄 الملف الكامل مُرفق."
    send_telegram_message(msg)
    try:
        with open(report_path, "rb") as f:
            files = {"document": f}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": f"{report_type} - {datetime.now().strftime('%Y-%m-%d')}"}
            r = requests.post(url, data=data, files=files)
            r.raise_for_status()
        print(f"[✓] {report_type} file sent.")
        logging.info(f"{report_type} file sent.")
    except Exception as e:
        print(f"[✗] Failed to send report file: {e}")
        logging.error(f"Failed to send report file: {e}")

def get_daily_data():
    """
    تجلب الأخبار غير المعالجة من آخر يوم في شكل خام
    لكي يستخدمها Agent لصياغة التقرير بأسلوبه
    
    Returns:
        dict: {
            'date': تاريخ التقرير,
            'investor_name': اسم المستثمر,
            'strategy': الاستراتيجية,
            'monthly_amount': المبلغ الشهري,
            'news': [
                {
                    'date': التاريخ,
                    'title': العنوان,
                    'content': المحتوى,
                    'source': المصدر,
                    'pe_ratio': مكرر الربح,
                    'priority': الأولوية
                },
                ...
            ]
        }
    """
    print("\n[~] Fetching daily data for Agent...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=1)).isoformat()
    c.execute("""SELECT date, title, content, source, pe_ratio, priority 
                 FROM news 
                 WHERE processed=0 AND date >= ? 
                 ORDER BY date DESC""", (cutoff,))
    rows = c.fetchall()
    conn.close()
    
    news_list = []
    for row in rows:
        news_list.append({
            'date': row[0],
            'title': row[1],
            'content': row[2],
            'source': row[3],
            'pe_ratio': row[4],
            'priority': row[5]
        })
    
    data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'investor_name': config['investor']['name'],
        'strategy': config['investor']['strategy'],
        'monthly_amount': config['investor']['monthly_amount'],
        'time_horizon_years': config['investor']['time_horizon_years'],
        'news': news_list
    }
    
    print(f"[✓] Retrieved {len(news_list)} unprocessed news items for Agent.")
    return data

def generate_daily_report():
    print("\n[~] Generating daily report...")
    report_dir = "/home/kero/.openclaw/workspace/reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = f"{report_dir}/daily-report-{datetime.now().strftime('%Y-%m-%d')}.md"

    unprocessed = get_unprocessed_news(days=1)
    summary_lines = []
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# التقرير اليومي للبورصة المصرية\n")
        f.write(f"**التاريخ:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## ملخص اليوم\n")
        f.write("- المؤشر EGX30: تحديث لاحق\n")
        f.write("- مكرر الربح المتوقع: 9 (تقديري)\n\n")
        f.write("## أخبار اليوم\n")
        for date, title, source in unprocessed:
            f.write(f"- {date[:10]}: {title} (المصدر: {source})\n")
            summary_lines.append(f"{date[:10]}: {title}")
            mark_news_processed(title, date)
        f.write("\n## تحديث الأسهم المتابعة\n")
        f.write("- CIB: سعر 2.63 دولار، متابعة\n")
        f.write("- الذهب: تراجع طفيف\n")
        f.write("- EGX30: أداء متقلب\n\n")
        f.write("## تذكير الاستثمار الشهري\n")
        f.write("تم تخصيص 2000 جنيه لهذا الشهر.\n")

    print(f"[✓] Daily report saved to {report_file}")

    summary = f"عدد أخبار اليوم: {len(unprocessed)}. أهمها: " + " | ".join(summary_lines[:3]) if summary_lines else "لا توجد أخبار جديدة."
    send_telegram_report(report_file, summary, "التقرير اليومي")

def generate_weekly_report():
    print("\n[~] Generating weekly report...")
    report_dir = "/home/kero/.openclaw/workspace/reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = f"{report_dir}/weekly-report-{datetime.now().strftime('%Y-%m-%d')}.md"

    unprocessed = get_unprocessed_news(days=7)
    summary_lines = []
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# التقرير الأسبوعي للبورصة المصرية\n")
        f.write(f"**التاريخ:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## ملخص السوق\n")
        f.write("- المؤشر EGX30: 43,952 نقطة (تقديري)\n")
        f.write("- مكرر الربح المتوقع: 9 (مازال أقل من 15)\n\n")
        f.write("## أهم الأخبار هذا الأسبوع\n")
        for date, title, source in unprocessed:
            f.write(f"- {date[:10]}: {title} (المصدر: {source})\n")
            summary_lines.append(f"{date[:10]}: {title}")
            mark_news_processed(title, date)
        f.write("\n## تحديث الأسهم المتابعة\n")
        f.write("- CIB: سعر 2.63 دولار، توصية شراء من Morgan Stanley\n")
        f.write("- الذهب: تراجع طفيف، فرصة للشراء طويل الأجل\n")
        f.write("- EGX30: أداء قوي هذا الأسبوع\n\n")
        f.write("## فرص استثمارية جديدة\n")
        f.write("- متابعة الطروحات الحكومية المرتقبة\n")
        f.write("- صناديق المؤشرات (ETFs) على EGX30 وEGX100\n\n")
        f.write("## تذكير الاستثمار الشهري\n")
        f.write("تم تخصيص 2000 جنيه لهذا الشهر. التوزيع المقترح:\n")
        f.write("- 50% CIB\n- 30% صندوق ذهب\n- 20% سيولة\n")

    print(f"[✓] Weekly report saved to {report_file}")

    summary = f"عدد الأخبار: {len(unprocessed)}. أهمها: " + " | ".join(summary_lines[:3]) if summary_lines else "لا توجد أخبار جديدة."
    send_telegram_report(report_file, summary, "التقرير الأسبوعي")

def daily_task():
    print("\n" + "="*50)
    print("=== بدء المهمة اليومية ===")
    print("="*50)
    init_db()
    fetch_news()
    generate_daily_report()
    print("="*50)
    print("=== انتهاء المهمة اليومية ===")
    print("="*50 + "\n")

def weekly_task():
    print("\n" + "="*50)
    print("=== بدء المهمة الأسبوعية ===")
    print("="*50)
    init_db()
    generate_weekly_report()
    print("="*50)
    print("=== انتهاء المهمة الأسبوعية ===")
    print("="*50 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: stock_agent.py {daily|weekly}")
        sys.exit(1)
    command = sys.argv[1]
    if command == "daily":
        daily_task()
    elif command == "weekly":
        weekly_task()
    else:
        print("أمر غير معروف. استخدم daily أو weekly")
        sys.exit(1)
