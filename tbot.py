import os
import re
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")


# Optional: Set up basic logging (you can remove if not needed)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- DeepSeek API function ---
def check_english_with_deepseek(text: str, australian_mode: bool = False) -> str:
    if australian_mode:
        system_prompt = (
            "You are an experienced English teacher specialising in Australian English. "
            "Please check the following message and tell the user:\n"
            "1. Is it understandable and natural-sounding to native Australian English speakers?\n"
            "2. How can they improve it—considering Australian spelling (e.g., 'colour', 'realise'), "
            "common phrasing, idioms (e.g., 'arvo', 'no worries', 'she'll be right'), and cultural fluency?\n"
            "Be encouraging, clear, and give examples where helpful."
        )
    else:
        system_prompt = (
            "You are an experienced English teacher. Please check the following message and tell me:\n"
            "1. Is it understandable to native English speakers?\n"
            "2. How can I improve it (grammar, word choice, fluency, etc.)?\n"
            "Be clear, friendly, and constructive."
        )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",  # Adjust if you're using a different model
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "❌ Sorry, I couldn’t process your message right now. Please try again later."

# --- Telegram Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "Hi! I’m your AI English teacher 🧠\n\n"
        "Send me any English sentence, and I’ll check it for clarity and correctness.\n\n"
        "👉 For **Australian English** feedback, add `#au` or `/au` at the end:\n"
        "_Example: “I seen him at the servo. #au”_\n\n"
        "Let’s improve your English together! 💬"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original_text = update.message.text.strip()

    # Detect Australian English mode
    australian_mode = bool(re.search(r'\s*(#au|/au)\b', original_text, re.IGNORECASE))

    # Remove the tag from the actual message content
    clean_text = re.sub(r'\s*(#au|/au)\b', '', original_text, flags=re.IGNORECASE).strip()

    if not clean_text:
        await update.message.reply_text(
            "Please send a message to check! Add `#au` for Australian English feedback.",
            parse_mode="Markdown"
        )
        return

    # Show typing indicator
    await update.message.chat.send_action(action="typing")

    # Get feedback from DeepSeek
    feedback = check_english_with_deepseek(clean_text, australian_mode=australian_mode)

    # Send response
    await update.message.reply_text(feedback, parse_mode="Markdown")

# --- Main function ---
def main():
    if not TELEGRAM_BOT_TOKEN or not DEEPSEEK_API_KEY:
        raise ValueError("Please set TELEGRAM_BOT_TOKEN and DEEPSEEK_API_KEY as environment variables.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
