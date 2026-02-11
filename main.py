import os
import re
import threading
from fastapi import FastAPI
import uvicorn

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- HTTP SERVER (Koyeb requirement) ----------------

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

def start_http():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ---------------- TELEGRAM BOT ----------------

BAD_TOKENS = [
    "zlib", "z_library", "z-library",
    "1lib", "libgen", "pdfdrive", "sk"
]

PERSONAL_TAG = "@ebookguy"

def clean_filename(filename: str) -> str:
    if "." not in filename:
        return filename

    name, ext = filename.rsplit(".", 1)
    name = name.replace("_", " ")

    for token in BAD_TOKENS:
        name = re.sub(
            rf"\b{re.escape(token)}\b",
            "",
            name,
            flags=re.IGNORECASE
        )

    name = re.sub(r"\s+", " ", name).strip()
    name = f"{name} - {PERSONAL_TAG}"

    return f"{name}.{ext}"

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    doc = message.document
    new_name = clean_filename(doc.file_name)

    file = await doc.get_file()
    await message.reply_document(
        document=file.file_id,
        filename=new_name
    )

    if message.chat.type == "channel":
        try:
            await message.delete()
        except Exception:
            pass

def start_bot():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN missing")

    app_bot = ApplicationBuilder().token(token).build()
    app_bot.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app_bot.run_polling()

# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    threading.Thread(target=start_http).start()
    start_bot()