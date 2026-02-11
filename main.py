import os
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

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

    # Send renamed file
    await message.reply_document(
        document=file.file_id,
        filename=new_name
    )

    # Auto-delete original ONLY in channels
    if message.chat.type == "channel":
        try:
            await message.delete()
        except Exception:
            # Fail silently (permissions / Telegram limits)
            pass

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document
        )
    )

    app.run_polling()

if __name__ == "__main__":
    main()
