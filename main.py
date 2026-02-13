import os
import re
import io

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

BAD_TOKENS = [
    "zlib",
    "z_library",
    "z-library",
    "1lib",
    "libgen",
    "pdfdrive",
    "sk"
]

PERSONAL_TAG = "@ebookguy"

# ---------------- APP INIT ----------------

app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ---------------- CLEAN FILENAME ----------------

def clean_filename(filename: str) -> str:
    if "." not in filename:
        return filename

    name, ext = filename.rsplit(".", 1)
    separators = r"[_\-\s,\.]"

    for token in BAD_TOKENS:
        name = re.sub(
            rf"(^|{separators}){re.escape(token)}(?={separators}|$)",
            " ",
            name,
            flags=re.IGNORECASE
        )

    name = name.replace("_", " ")
    name = re.sub(r"[,\.\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if PERSONAL_TAG.lower() not in name.lower():
        name = f"{name} - {PERSONAL_TAG}"

    return f"{name}.{ext}"

# ---------------- HANDLER ----------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    doc = message.document

    new_name = clean_filename(doc.file_name)

    tg_file = await doc.get_file()
    buffer = io.BytesIO()
    await tg_file.download_to_memory(out=buffer)
    buffer.seek(0)

    await message.reply_document(
        document=buffer,
        filename=new_name
    )

    if message.chat.type == "channel":
        try:
            await message.delete()
        except Exception:
            pass

telegram_app.add_handler(
    MessageHandler(filters.Document.ALL, handle_document)
)

# ---------------- WEBHOOK ----------------

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.get("/")
@app.head("/")
async def health():
    return {"status": "ok"}

# ---------------- STARTUP ----------------

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        raise RuntimeError("RENDER_EXTERNAL_URL missing")

    await telegram_app.bot.set_webhook(
        url=f"{render_url}/webhook"
    )

@app.on_event("shutdown")
async def shutdown():
    await telegram_app.shutdown()