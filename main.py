import logging
from pyrogram import Client, filters
from pymongo import MongoClient
from config import BOT_TOKEN, MONGO_DB_URI, ADMIN_USER_ID, BOT_USERNAME

API_ID = 28476396
API_HASH = "6d30f0d3b7cc4dbb8a836aa292bb5b52"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = MongoClient(MONGO_DB_URI) if MONGO_DB_URI and "YOUR_MONGODB_URI_HERE" not in MONGO_DB_URI else None
if mongo:
    db = mongo["FileStoreDB"]
    files = db.files
else:
    files = None
    logger.warning("MongoDB URI not set or left as placeholder. The bot will not save file metadata until you set MONGO_DB_URI in config.py")

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if len(message.command) > 1:
        param = message.command[1]
        if files:
            doc = files.find_one({"file_id": param})
        else:
            doc = None
        if not doc:
            await message.reply_text("❌ File not found or may have been deleted.")
            return
        try:
            await client.send_cached_media(chat_id=message.chat.id, file_id=doc["tg_file_id"], caption=doc.get("caption", ""))
        except Exception as e:
            logger.exception("Failed to send file:")
            await message.reply_text("⚠️ Failed to send the file. It might be too old or removed from Telegram.")
    else:
        await message.reply_text(
            "👋 Welcome to SR SSC GK File Bot!\n\n"
            "📥 How to use:\n"
            "• Admin (only) — send a file to this bot to save it.\n"
            "• After saving, the bot will reply with a share link.\n"
            "• Anyone sending that link (or clicking it) will receive the file.\n\n"
            "Use /help for more information."
        )

@bot.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    await message.reply_text(
        "**📚 File Store Bot Help**\n\n"
        "🧑‍💻 Only admin can upload files.\n"
        "📤 Admin sends a file → bot saves and returns a share link.\n"
        "📥 Users open the share link or send it to the bot → they get the file.\n\n"
        "Bot username: @{username}".format(username=BOT_USERNAME)
    )

@bot.on_message(filters.user(ADMIN_USER_ID) & (filters.document | filters.video | filters.audio | filters.photo | filters.voice))
async def save_file(client, message):
    media = message.document or message.video or message.audio or message.photo or message.voice
    if not media:
        await message.reply_text("Send a supported file (document, video, audio, photo, voice).")
        return

    tg_file_id = media.file_id
    if files and files.find_one({"file_id": tg_file_id}):
        await message.reply_text("⚠️ This file is already saved.")
        return

    if files:
        files.insert_one({
            "file_id": tg_file_id,
            "tg_file_id": tg_file_id,
            "caption": message.caption or "",
        })
        share_link = f"https://t.me/{BOT_USERNAME}?start={tg_file_id}"
        await message.reply_text(f"✅ File saved!\n\n🔗 Share Link:\n{share_link}")
    else:
        await message.reply_text("⚠️ MongoDB is not configured. Please set MONGO_DB_URI in config.py and restart the bot.")

@bot.on_message(filters.private & ~filters.user(ADMIN_USER_ID))
async def echo_private(client, message):
    text = (message.text or "").strip()
    param = None
    if text.startswith("https://t.me/"):
        if "start=" in text:
            param = text.split("start=")[-1]
    elif text.startswith("/start "):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            param = parts[1]
    else:
        param = text if text else None

    if param:
        if files:
            doc = files.find_one({"file_id": param})
        else:
            doc = None
        if not doc:
            await message.reply_text("❌ File not found. Make sure the link is correct.")
            return
        try:
            await client.send_cached_media(chat_id=message.chat.id, file_id=doc["tg_file_id"], caption=doc.get("caption", ""))
        except Exception as e:
            logger.exception("Failed to send file:")
            await message.reply_text("⚠️ Failed to send the file. It might be removed or restricted.")
    else:
        await message.reply_text("Send a file share link or file-id to get the file.\nIf you need help, send /help.")

if __name__ == '__main__':
    print("Starting bot... (make sure you edited config.py with BOT_TOKEN and MONGO_DB_URI)")
    bot.run()
