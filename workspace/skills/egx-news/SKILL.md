```skill
---
name: egx-news
description: متابعة وتحليل البورصة المصرية (EGX30, CIB, الذهب). يجلب الأخبار مع Double-Check، ينشئ تقارير يومية وأسبوعية، ويرسل إشعارات Telegram للأخبار المهمة فقط.
homepage: https://www.egx.com.eg
metadata: {"clawdbot":{"emoji":"🇪🇬","requires":{"bins":["uv"],"env":[]}}}
---

# Egypt Stocks (EGX) - مساعد الاستثمار

مساعد استثماري للبورصة المصرية. مصمم لـ **Kero** - مستثمر طويل الأجل (5 سنين).

## معلومات المستثمر
- **المبلغ الشهري:** 2000 جنيه
- **بداية الاستثمار:** 28 فبراير 2026
- **القطاعات:** البنوك (CIB)، الذهب، المؤشرات (EGX30, EGX100)

---

## الأوامر المتاحة

### 1. جلب الأخبار مع Double-Check
```bash
uv run {baseDir}/scripts/fetch_news.py
uv run {baseDir}/scripts/fetch_news.py --days 7
uv run {baseDir}/scripts/fetch_news.py --symbol CIB
uv run {baseDir}/scripts/fetch_news.py --live    # جلب أخبار حية من Google News RSS
uv run {baseDir}/scripts/fetch_news.py --raw     # جلب الأخبار الخام للـ LLM
```
**المخرجات:** JSON بالأخبار الموثوقة فقط

### 2. التقرير اليومي
```bash
uv run {baseDir}/scripts/daily_report.py
uv run {baseDir}/scripts/daily_report.py --no-send   # إنشاء التقرير بدون إرسال Telegram
```
**المخرجات:** تقرير markdown + ملخص JSON + إرسال Telegram

### 3. التقرير الأسبوعي
```bash
uv run {baseDir}/scripts/weekly_report.py
uv run {baseDir}/scripts/weekly_report.py --no-send  # إنشاء التقرير بدون إرسال Telegram
```
**المخرجات:** تقرير شامل markdown + ملخص JSON + إرسال Telegram

### 4. إرسال إشعار Telegram
```bash
uv run {baseDir}/scripts/send_telegram.py "الرسالة هنا"
uv run {baseDir}/scripts/send_telegram.py --file /path/to/report.md "ملخص"
uv run {baseDir}/scripts/send_telegram.py --file /path/to/report.md --summarize        # تلخيص تلقائي (regex)
uv run {baseDir}/scripts/send_telegram.py --file /path/to/report.md --summarize-llm    # تلخيص بالذكاء الاصطناعي (LLM)
uv run {baseDir}/scripts/send_telegram.py --file /path/to/report.md --summarize-llm --provider chatanywhere
```

### 5. خدمة التلخيص بالذكاء الاصطناعي (LLM)
```bash
uv run {baseDir}/scripts/llm_service.py "نص للتلخيص"
uv run {baseDir}/scripts/llm_service.py --file /path/to/report.md
uv run {baseDir}/scripts/llm_service.py --file /path/to/report.md --provider chatanywhere --max-length 200
```

---

## قواعد Double-Check (إلزامية)

قبل أي خبر يتم اعتماده:

| القاعدة | المعيار |
|---------|---------|
| ✅ المصدر موثوق | Morgan Stanley, HC, Faros, CNBC Arabic, مباشر, Investing.com |
| ✅ مكرر الربحية | PE ≤ 15 |
| ✅ كلمات طويل الأجل | استثمار، نمو، أساسيات قوية، احتفاظ، عوائد |
| ❌ ليس من Blacklist | Twitter, Facebook, تلجرام مجهول |

---

## مستويات الإشعارات

| المستوى | المعيار | الإجراء |
|---------|---------|---------|
| **high** | تغيير توصية، حدث اقتصادي كبير، Morgan Stanley | إشعار Telegram فوري |
| **medium** | أرباح فصلية، فرصة استثمار جديدة | ضمن التقرير |
| **low** | سعر مناسب، أخبار روتينية | ضمن التقرير فقط |

---

## متى لا نرسل إشعارات؟

- أخبار من مصادر غير موثوقة
- أخبار قصيرة الأجل أو مضاربية  
- تكرار نفس الخبر
- أي شيء لا يمر بـ Double-Check
- PE > 15

---

## الجدولة الموصى بها

| المهمة | التوقيت | الأمر |
|--------|---------|-------|
| فحص يومي | 7:00 ص | `daily_report.py` |
| تقرير أسبوعي | السبت 9:00 ص | `weekly_report.py` |

---

## أمثلة الاستخدام

### فحص أخبار اليوم
```
أنت: "إيه أخبار البورصة النهاردة؟"
→ الـ Agent يشغل: uv run {baseDir}/scripts/fetch_news.py --days 1
→ يرد بملخص الأخبار الموثوقة
```

### طلب تقرير
```
أنت: "عملي تقرير الأسبوع"
→ الـ Agent يشغل: uv run {baseDir}/scripts/weekly_report.py
→ يبعت التقرير على Telegram
```

### سؤال عن سهم
```
أنت: "إيه وضع CIB؟"
→ الـ Agent يشغل: uv run {baseDir}/scripts/fetch_news.py --symbol CIB
→ يرد بآخر أخبار وتوصيات CIB
```

---

## Config

الإعدادات في: `{baseDir}/config.json`

---

## ملاحظات مهمة

1. **Double-Check إلزامي** - لا يتم إرسال أي خبر بدون تمريره
2. **JSON output** - كل الـ scripts تطبع JSON للـ Agent
3. **لا إزعاج** - فقط الأخبار المهمة تستحق إشعار فوري
4. **طويل الأجل فقط** - تجاهل أي خبر مضاربي أو قصير الأجل
5. **التلخيص الذكي** - تدعم التقارير إمكانية التلخيص بواسطة (LLM)
```

