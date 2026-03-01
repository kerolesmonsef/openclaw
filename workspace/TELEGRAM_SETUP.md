# Telegram Bot Configuration
# Set up your Telegram bot to receive stock analysis notifications

## Step 1: Create a Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/start` to begin
3. Send `/newbot` to create a new bot
4. Choose a name for your bot (e.g., "StockAnalysisBot")
5. Choose a username ending with "_bot" (e.g., "StockAnalysisBot")
6. **BotFather will give you an API token** - save this!

## Step 2: Get Your Chat ID
1. Open your new bot in Telegram (search for the username)
2. Send any message to the bot (e.g., "Hello")
3. Open this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for the "chat" object and find the "id" field - this is your CHAT_ID

## Step 3: Configure the Script
1. Edit the telegram-notifier.sh file:
   ```bash
   nano /home/kero/.openclaw/workspace/telegram-notifier.sh
   ```
2. Replace the placeholder values:
   ```bash
   TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
   TELEGRAM_CHAT_ID="YOUR_CHAT_ID_HERE"
   ```
3. Save and exit (Ctrl+X, then Y, then Enter)

## Step 4: Test the Configuration
1. Test the bot:
   ```bash
   /home/kero/.openclaw/workspace/telegram-notifier.sh test
   ```
2. Check your Telegram - you should receive a test message

## Step 5: Update the Main Controller
1. Edit the stock-analysis-controller.sh:
   ```bash
   nano /home/kero/.openclaw/workspace/stock-analysis-controller.sh
   ```
2. Add Telegram notification calls in the appropriate places
3. Save and exit

## Configuration Complete!
Your Telegram bot is now ready to receive stock analysis notifications.

**Important:** Keep your bot token and chat ID private - don't share them with anyone!