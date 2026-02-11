import os
import re
import io
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

# ---------------- HTTP SERVER (Render requirement) ----------------

web_app = FastAPI()

@web_app.get("/")
def health():
    return {"status": "ok"}

def start_http():
    port = int(os.environ.get("PORT", 10000))  # Render default
    uvicorn.run(web_app, host="0.0.0.0", port=port)

# ---------------- BOT CONFIG ----------------

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

# ---------------- FILENAME CLEANER ----------------

def clean_filename(filename: str) -> str:
    if "." not in filename:
        return filename

    name, ext = filename.rsplit(".", 1)

    # Remove junk tokens with safe boundaries
    for token in BAD_TOKENS:
        name = re.sub(
            rf"(^|[_\-\s]){re.escape(token)}([_\-\s]|$)",
            " ",
            name,
            flags=re.IGNORECASE
        )

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Normalize spaces
    name = re.sub(r"\s+", " ", name).strip()

    # Append personal tag
    name = f"{name} - {PERSONAL_TAG}"

    return f"{name}.{ext}"

# ---------------- DOCUMENT HANDLER ----------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    doc = message.document

    new_name = clean_filename(doc.file_name)

    # Download file into memory
    tg_file = await doc.get_file()
    buffer = io.BytesIO()
    await tg_file.download_to_memory(out=buffer)
    buffer.seek(0)

    # Re-upload with new filename
    await message.reply_document(
        document=buffer,
        filename=new_name
    )

    # Delete original ONLY in channels
    if message.chat.type == "channel":
        try:
            await message.delete()
        except Exception:
            pass

# ---------------- BOT START ----------------

def start_bot():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    threading.Thread(target=start_http).start()
    start_bot()