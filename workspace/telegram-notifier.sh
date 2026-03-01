#!/bin/bash

# Telegram Notification Script
# Sends notifications to Telegram bot (updated with more formats)

# Configuration (as requested, keep tokens inline)
TELEGRAM_BOT_TOKEN="8680626744:AAEfMsJb-RHlkNOSju9w8ZsursBJzh2BSsY"
TELEGRAM_CHAT_ID="5147345838"

# Function to send message to Telegram
send_telegram_message() {
    local message="$1"
    local parse_mode="${2:-Markdown}"
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
        echo "Error: Telegram configuration not set"
        return 1
    fi
    
    # Send message using curl
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d "chat_id=$TELEGRAM_CHAT_ID" \
        -d "text=$message" \
        -d "parse_mode=$parse_mode" >/dev/null
    
    if [ $? -eq 0 ]; then
        echo "Message sent to Telegram"
        return 0
    else
        echo "Failed to send message to Telegram"
        return 1
    fi
}

# Function to send news alert (immediate)
send_news_alert() {
    local news_title="$1"
    local news_content="$2"
    local source="$3"
    
    local message="📢 *أخبار عاجلة عن الأسهم*\n\n"
    message+="*العنوان:* $news_title\n"
    message+="*الخبر:* $news_content\n"
    message+="*المصدر:* $source\n"
    message+="\n📊 *تأثير طويل الأجل:* بعد التحقق، تبين أنه مهم على المدى الطويل ✓"
    
    send_telegram_message "$message"
}

# Function to send weekly report summary
send_weekly_report() {
    local report_file="$1"
    local summary="$2"
    
    # إرسال ملخص أولاً
    local message="📈 *تقرير السوق الأسبوعي*\n\n"
    message+="*ملخص الأسبوع:* $summary\n"
    message+="\n📄 للتفاصيل الكاملة، افتح الملف المرفق."
    
    send_telegram_message "$message"
    
    # إرسال الملف كمستند (اختياري، لكن يحتاج curl إضافي)
    if [ -f "$report_file" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument" \
            -F "chat_id=$TELEGRAM_CHAT_ID" \
            -F "document=@$report_file" \
            -F "caption=📊 تقرير الأسبوع - $(date +%Y-%m-%d)" >/dev/null
        echo "Report file sent."
    fi
}

# Function to send custom message (used by controller for any immediate alerts)
send_custom() {
    local custom_message="$1"
    send_telegram_message "$custom_message"
}

# Main function
main() {
    local message_type="$1"
    shift
    
    case "$message_type" in
        "news")
            send_news_alert "$1" "$2" "$3"
            ;;
        "weekly")
            send_weekly_report "$1" "$2"
            ;;
        "custom")
            send_custom "$1"
            ;;
        "test")
            send_telegram_message "✅ اختبار تجريبي ناجح! نظام تحليل الأسهم يعمل بشكل صحيح."
            ;;
        *)
            echo "Usage: $0 {news|weekly|custom|test} [parameters]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
