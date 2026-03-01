# 🚀 اقتراحات التحسين - Egypt Stocks Agent

## 📊 تحسينات لجلب أخبار أوضح وأدق

### 1️⃣ إضافة مصادر متخصصة

**المشكلة:** Google News يجلب أخبار عامة  
**الحل:** إضافة مصادر متخصصة في البورصة

```python
# مصادر مقترحة للإضافة
SPECIALIZED_SOURCES = [
    # مصادر مصرية متخصصة
    "https://www.mubasher.info/countries/eg/news",  # مباشر مصر
    "https://www.alborsanews.com/rss",              # جريدة البورصة
    "https://amfrss.amwal-mag.com/rss.xml",         # أموال الغد
    
    # تحليلات دولية
    "https://www.reuters.com/markets/",              # Reuters Markets
    "https://www.bloomberg.com/middleeast",          # Bloomberg ME
]
```

**التنفيذ:** 
- إضافة RSS feeds متعددة
- دمج الأخبار من كل المصادر
- إزالة التكرار

---

### 2️⃣ تحليل المشاعر (Sentiment Analysis)

**الفكرة:** تحديد إذا الخبر إيجابي/سلبي/محايد

```python
def analyze_sentiment(text):
    """تحليل مشاعر الخبر"""
    positive_words = ['صعود', 'ارتفاع', 'مكاسب', 'نمو', 'أرباح', 'قياسي', 'إيجابي']
    negative_words = ['هبوط', 'انخفاض', 'خسائر', 'تراجع', 'سلبي', 'حرب', 'أزمة']
    
    text_lower = text.lower()
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        return {'sentiment': 'positive', 'score': pos_count / (pos_count + neg_count + 1)}
    elif neg_count > pos_count:
        return {'sentiment': 'negative', 'score': neg_count / (pos_count + neg_count + 1)}
    else:
        return {'sentiment': 'neutral', 'score': 0.5}
```

**الفائدة:**
- تصنيف الأخبار: 🟢 إيجابي / 🔴 سلبي / ⚪ محايد
- تنبيه عند تغير المزاج العام
- مساعدة في قرارات البيع/الشراء

---

### 3️⃣ تتبع الأسهم المحددة (Stock Watchlist)

**الفكرة:** مراقبة أسهم معينة وتنبيه عند أي خبر عنها

```json
// في config.json
"watchlist": {
    "CIB": {"priority": "high", "alert": true},
    "EGX30": {"priority": "high", "alert": true},
    "QNBA": {"priority": "medium", "alert": true},
    "GOLD": {"priority": "medium", "alert": true}
}
```

**التنفيذ:**
- إشعار فوري عند أي خبر عن سهم في الـ watchlist
- تجميع أخبار كل سهم في قسم خاص في التقرير

---

### 4️⃣ مؤشر اتجاه السوق (Market Trend Indicator)

**الفكرة:** تحليل الأخبار لاستنتاج اتجاه السوق

```python
def calculate_market_trend(news_list):
    """حساب مؤشر اتجاه السوق من الأخبار"""
    sentiments = [analyze_sentiment(n['title'] + ' ' + n['content']) for n in news_list]
    
    positive = len([s for s in sentiments if s['sentiment'] == 'positive'])
    negative = len([s for s in sentiments if s['sentiment'] == 'negative'])
    total = len(sentiments)
    
    if total == 0:
        return {'trend': 'unknown', 'confidence': 0}
    
    trend_score = (positive - negative) / total
    
    if trend_score > 0.3:
        return {'trend': '📈 صاعد', 'confidence': trend_score, 'recommendation': 'فرصة شراء محتملة'}
    elif trend_score < -0.3:
        return {'trend': '📉 هابط', 'confidence': abs(trend_score), 'recommendation': 'حذر - انتظر'}
    else:
        return {'trend': '➡️ متذبذب', 'confidence': 0.5, 'recommendation': 'راقب السوق'}
```

---

## 🎯 تحسينات للتنبؤ والتحليل

### 5️⃣ تحليل الأنماط الزمنية

**الفكرة:** تتبع تكرار الأخبار الإيجابية/السلبية عبر الوقت

```python
def detect_news_pattern(days=30):
    """اكتشاف أنماط في الأخبار"""
    # جلب أخبار آخر 30 يوم
    # تحليل الاتجاه اليومي
    # اكتشاف إذا كان هناك نمط متكرر
    
    patterns = {
        'weekly_positive_days': [],      # أيام الأسبوع الإيجابية
        'event_based_changes': [],        # تغيرات بسبب أحداث
        'sector_momentum': {}             # زخم القطاعات
    }
    return patterns
```

---

### 6️⃣ ربط مع بيانات الأسعار (Yahoo Finance)

**الفكرة:** جلب أسعار فعلية ومقارنتها بالأخبار

```python
# إضافة yfinance
# pip install yfinance

import yfinance as yf

def get_stock_data(symbol):
    """جلب بيانات السهم من Yahoo Finance"""
    ticker = yf.Ticker(f"{symbol}.CA")  # .CA للأسهم المصرية
    
    info = ticker.info
    history = ticker.history(period="1mo")
    
    return {
        'current_price': info.get('currentPrice'),
        'pe_ratio': info.get('trailingPE'),
        'change_percent': info.get('regularMarketChangePercent'),
        '52w_high': info.get('fiftyTwoWeekHigh'),
        '52w_low': info.get('fiftyTwoWeekLow'),
        'volume': info.get('volume'),
        'history': history
    }
```

**الفائدة:**
- PE Ratio حقيقي بدلاً من null
- مقارنة السعر الحالي مع الأخبار
- تحديد فرص الشراء (السهم قرب 52w_low + أخبار إيجابية)

---

## 👤 تحسينات User Experience

### 7️⃣ ملخص تفاعلي على Telegram

**بدلاً من:**
```
📊 تقرير 2026-02-28
عدد الأخبار: 15 | عاجل: 3
```

**نستخدم:**
```
📊 تقرير البورصة | 28 فبراير

🟢 المزاج العام: إيجابي (70%)
📈 EGX30: صاعد +2.3%

🔔 أهم 3 أخبار:
1. صعود جماعي للمؤشرات
2. CIB يحقق أرباح قياسية  
3. إطلاق سوق المشتقات غداً

💡 التوصية: فرصة جيدة للشراء التدريجي

[📄 التقرير الكامل]
```

---

### 8️⃣ أزرار تفاعلية (Inline Buttons)

```python
def send_with_buttons(message):
    """إرسال رسالة مع أزرار تفاعلية"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📊 تفاصيل CIB", "callback_data": "details_CIB"},
                {"text": "📈 تفاصيل EGX30", "callback_data": "details_EGX30"}
            ],
            [
                {"text": "📰 كل الأخبار", "callback_data": "all_news"},
                {"text": "⚙️ الإعدادات", "callback_data": "settings"}
            ]
        ]
    }
    # إرسال مع الأزرار
```

---

### 9️⃣ إحصائيات بصرية (Charts)

**الفكرة:** إنشاء رسوم بيانية وإرسالها كصور

```python
import matplotlib.pyplot as plt

def create_weekly_chart(data):
    """إنشاء رسم بياني للأسبوع"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # رسم اتجاه السوق
    ax.plot(data['dates'], data['sentiment_scores'], 'b-', label='مؤشر المزاج')
    ax.fill_between(data['dates'], data['sentiment_scores'], alpha=0.3)
    
    plt.title('اتجاه السوق خلال الأسبوع', fontsize=14)
    plt.savefig('weekly_chart.png', dpi=150, bbox_inches='tight')
    
    return 'weekly_chart.png'
```

---

### 🔟 تنبيهات ذكية مخصصة

**الفكرة:** تنبيهات حسب تفضيلات المستخدم

```json
// في config.json
"smart_alerts": {
    "price_drop": {
        "threshold": -5,           // تنبيه عند انخفاض 5%
        "action": "immediate"
    },
    "positive_news_streak": {
        "threshold": 3,            // 3 أخبار إيجابية متتالية
        "action": "daily_summary"
    },
    "sector_change": {
        "sectors": ["banks", "gold"],
        "action": "immediate"
    }
}
```

---

## 🛠️ تحسينات تقنية

### 1️⃣ تخزين أفضل (Cache)

```python
import functools
import time

@functools.lru_cache(maxsize=100)
def cached_fetch_news(query, ttl_hash=None):
    """جلب الأخبار مع caching"""
    del ttl_hash  # للتجاوز كل ساعة
    return fetch_raw_news_from_google()

def get_ttl_hash(seconds=3600):
    return round(time.time() / seconds)
```

---

### 2️⃣ معالجة الأخطاء

```python
import logging

logging.basicConfig(
    filename='~/.openclaw/skills/egx-news/logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def safe_fetch():
    try:
        return fetch_raw_news_from_google()
    except requests.Timeout:
        logging.warning("Timeout fetching news")
        return use_cached_data()
    except Exception as e:
        logging.error(f"Error: {e}")
        send_telegram_error_alert(str(e))
        raise
```

---

### 3️⃣ اختبارات تلقائية

```python
# tests/test_fetch_news.py
def test_double_check():
    """اختبار فلترة الأخبار"""
    trusted_news = {"title": "CIB أرباح", "source": "الأهرام", "pe_ratio": 10}
    untrusted_news = {"title": "شائعات", "source": "twitter.com", "pe_ratio": None}
    
    assert double_check_news(**trusted_news)[0] == True
    assert double_check_news(**untrusted_news)[0] == False
```

---

## 📋 ملخص الأولويات

| الأولوية | التحسين | الجهد | الأثر |
|----------|---------|-------|-------|
| 🔴 عالية | تحليل المشاعر | متوسط | عالي |
| 🔴 عالية | ربط Yahoo Finance | متوسط | عالي |
| 🟡 متوسطة | مصادر متخصصة | منخفض | متوسط |
| 🟡 متوسطة | ملخص تفاعلي | متوسط | عالي |
| 🟢 منخفضة | رسوم بيانية | عالي | متوسط |
| 🟢 منخفضة | أزرار تفاعلية | متوسط | متوسط |

---

## 🎯 خطة التنفيذ المقترحة

### المرحلة 1 (أسبوع واحد):
- [ ] إضافة تحليل المشاعر البسيط
- [ ] تحسين الملخص على Telegram
- [ ] إضافة مؤشر اتجاه السوق

### المرحلة 2 (أسبوعين):
- [ ] ربط مع Yahoo Finance
- [ ] إضافة Watchlist
- [ ] تنبيهات ذكية

### المرحلة 3 (شهر):
- [ ] رسوم بيانية
- [ ] أزرار تفاعلية
- [ ] تحليل الأنماط الزمنية

---

**هل تريد أن أبدأ بتنفيذ أي من هذه التحسينات؟**
