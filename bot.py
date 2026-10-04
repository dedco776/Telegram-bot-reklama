import os
import time
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Render va UptimeRobot uchun veb-server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot 24/7 ishlamoqda!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

user_cooldowns = {}
ads_database = {
    "👕 Tekstil va Kiyimlar": [
        {"id": 1, "text": "👕 Uzum Marketda kiyim-kechaklarga 50% chegirma!", "link": "https://uzum.uz", "views": 0, "likes": 0}
    ],
    "📱 Texnika va Gadjetlar": [
        {"id": 2, "text": "📱 Arzon iPhone va maishiy texnika do'koni!", "link": "https://uzum.uz", "views": 0, "likes": 0}
    ],
    "🍕 Oziq-ovqat va Restoran": [
        {"id": 3, "text": "🍕 Yevropa taomlari va fast-fud yetkazib berish xizmati!", "link": "https://uzum.uz", "views": 0, "likes": 0}
    ]
}

# Pastki klaviatura menyulari
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛍 Do'konlar va Aksiyalar")],
        [KeyboardButton("📊 Mening reklamalarim"), KeyboardButton("📢 Reklama joylashtirish")]
    ],
    resize_keyboard=True
)

CATEGORIES_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("👕 Tekstil va Kiyimlar")],
        [KeyboardButton("📱 Texnika va Gadjetlar")],
        [KeyboardButton("🍕 Oziq-ovqat va Restoran")],
        [KeyboardButton("⬅️ Bosh menyu")]
    ],
    resize_keyboard=True
)

# Start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! Reklama va aksiyalar botiga xush kelibsiz.\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=MAIN_KEYBOARD
    )

# Matnli xabarlarga ishlov berish (Pastki tugmalar uchun)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "⬅️ Bosh menyu":
        await update.message.reply_text("Bosh menyudasiz:", reply_markup=MAIN_KEYBOARD)

    elif text == "🛍 Do'konlar va Aksiyalar":
        await update.message.reply_text("Qaysi bo'limdagi reklamalarni ko'rmoqchisiz?", reply_markup=CATEGORIES_KEYBOARD)

    elif text in ads_database:
        current_time = time.time()
        
        # 1 daqiqalik (60 sek) Taymer tekshiruvi
        if user_id in user_cooldowns:
            passed_time = current_time - user_cooldowns[user_id]
            if passed_time < 60:
                wait_time = int(60 - passed_time)
                await update.message.reply_text(f"⏳ Boshqa reklama ko'rish uchun {wait_time} soniya kuting!")
                return

        ads = ads_database[text]
        if not ads:
            await update.message.reply_text("Hozircha bu bo'limda reklama yo'q!")
            return

        selected_ad = random.choice(ads)
        selected_ad["views"] += 1
        user_cooldowns[user_id] = current_time

        # Reklama ostidagi Like va Link inline-tugmasi
        inline_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"❤️ Like ({selected_ad['likes']})", callback_data=f"like_{text}_{selected_ad['id']}"),
                InlineKeyboardButton("🔗 Saytga o'tish", url=selected_ad["link"])
            ]
        ])
        
        ad_text = f"<b>{selected_ad['text']}</b>\n\n👁 Ko'rishlar soni: {selected_ad['views']}"
        await update.message.reply_text(ad_text, parse_mode="HTML", reply_markup=inline_keyboard)

    elif text == "📊 Mening reklamalarim":
        msg = "📊 <b>Sizning aktiv reklamalaringiz statistikasi:</b>\n\n"
        for cat, ads in ads_database.items():
            for ad in ads:
                msg += f"📌 <b>Reklama:</b> {ad['text']}\n"
                msg += f"👁 Ko'rishlar: <b>{ad['views']}</b> ta | ❤️ Like'lar: <b>{ad['likes']}</b> ta\n"
                msg += "-------------------------\n"
        await update.message.reply_text(msg, parse_mode="HTML")

    elif text == "📢 Reklama joylashtirish":
        msg = (
            "📢 <b>Reklama joylashtirish uchun:</b>\n\n"
            "1. Reklamangiz turiga qarab bo'limni tanlang.\n"
            "2. To'lovni amalga oshiring (100,000 so'm / 1 oy).\n"
            "3. Admin bilan bog'lanib postni tasdiqlating.\n\n"
            "👨‍💻 <b>Admin aloqa:</b> @admin_profi"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

# Like tugmasini bosganda ishlaydi
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("like_"):
        _, category, ad_id = data.split("_")
        ad_id = int(ad_id)
        for ad in ads_database[category]:
            if ad["id"] == ad_id:
                ad["likes"] += 1
                await query.answer("Rahmat! Likingiz hisobga olindi.", show_alert=True)
                
                # Tugmadagi like sonini yangilash
                new_keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(f"❤️ Like ({ad['likes']})", callback_data=f"like_{category}_{ad['id']}"),
                        InlineKeyboardButton("🔗 Saytga o'tish", url=ad["link"])
                    ]
                ])
                await query.message.edit_reply_markup(reply_markup=new_keyboard)
                break

def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
