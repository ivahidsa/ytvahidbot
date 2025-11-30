import os
import yt_dlp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

user_data = {}

# --------------------------
# گرفتن کیفیت‌های قابل دانلود
# --------------------------

def get_formats(url):
    formats_list = []

    ydl_opts = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        for f in info.get("formats", []):
            if f.get("ext") == "mp4" and f.get("filesize"):
                label = f"{f['format_note']} - {round(f['filesize'] / 1024 / 1024, 1)} MB"
                formats_list.append((label, f['format_id']))

    return formats_list


# --------------------------
# گرفتن اطلاعات Playlist
# --------------------------

def inspect_playlist(url):
    ydl_opts = {"quiet": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    videos = info.get("entries", [])
    total_time = sum(v.get("duration", 0) for v in videos)

    return len(videos), total_time, videos


# --------------------------
# دانلود یک ویدئو
# --------------------------

async def download_and_send(message, url, format_id):
    await message.reply("⏳ در حال دانلود...")

    file_name = "video.mp4"

    ydl_opts = {
        "format": format_id,
        "outtmpl": file_name,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    await message.reply_video(open(file_name, "rb"))
    os.remove(file_name)


# --------------------------
# پیام ورودی (لینک)
# --------------------------

@dp.message_handler(content_types=['text'])
async def process_link(message: types.Message):
    url = message.text.strip()

    # اگر Playlist بود
    if "list=" in url:
        count, total_time, videos = inspect_playlist(url)

        minutes = total_time // 60

        user_data[message.chat.id] = {"videos": videos}

        await message.reply(
            f"🎵 این لینک یک پلی‌لیست است.\n\n"
            f"🔹 تعداد ویدئوها: {count}\n"
            f"🔹 مجموع زمان: {minutes} دقیقه\n\n"
            f"لطفاً کیفیت دانلود همه ویدئوها را انتخاب کنید."
        )

        # نمونه کیفیت‌ها از اولین ویدئو
        formats = get_formats(videos[0]["url"])

        kb = InlineKeyboardMarkup()
        for label, fid in formats:
            kb.add(InlineKeyboardButton(label, callback_data=f"pl_{fid}"))

        await message.reply("🔽 انتخاب کیفیت:", reply_markup=kb)
        return

    # اگر یک ویدئو بود
    formats = get_formats(url)

    if not formats:
        await message.reply("❌ فرمت ویدئو پیدا نشد.")
        return

    user_data[message.chat.id] = {"url": url}

    kb = InlineKeyboardMarkup()
    for label, fid in formats:
        kb.add(InlineKeyboardButton(label, callback_data=f"vid_{fid}"))

    await message.reply("🎬 کیفیت مورد نظر را انتخاب کنید:", reply_markup=kb)


# --------------------------
# انتخاب کیفیت (ویدئو/پلی‌لیست)
# --------------------------

@dp.callback_query_handler(lambda c: c.data.startswith("vid_") or c.data.startswith("pl_"))
async def callback_quality(call: types.CallbackQuery):
    format_id = call.data.split("_")[1]
    chat_id = call.message.chat.id

    if call.data.startswith("vid_"):
        url = user_data[chat_id]["url"]
        await download_and_send(call.message, url, format_id)

    elif call.data.startswith("pl_"):
        videos = user_data[chat_id]["videos"]

        await call.message.reply("📥 شروع دانلود پلی‌لیست...")

        for v in videos:
            await download_and_send(call.message, v["url"], format_id)

    await call.answer()


# --------------------------
# اجرای ربات
# --------------------------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
