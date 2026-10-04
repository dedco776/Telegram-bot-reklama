import os
import time
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Render o'chib qolmasligi uchun kichik veb-server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot 24/7 ishlamoqda!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

user_cooldowns = {}
ads_database = {
    "tekstil": [
        {"id": 1, "text": "👕 Uzum Marketda kiyim-kechaklarga 50% chegirma!", "link": "https://uzum.uz", "views": 0, "likes": 0}
    ],
    "texnika": [
        {"id": 2, "text": "📱 Arzon iPhone va maishiy texnika do'koni!", "link": "https://uzum.uz", "views": 0, "likes": 0}
    ],
    "ovqat": [
        {"id": 3, "text": "🍕 Yevropa taomlari va fast-fud yetkazib berish xizmati!", "link": "https://uzum.uz", "views": 0, "likes": 0}
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍 Do'konlar va Aksiyalar", callback_data="menu_categories")],
        [InlineKeyboardButton("📊 Mening reklamalarim", callback_data="my_ads")],
        [InlineKeyboardButton("📢 Reklama joylashtirish", callback_data="add_ad_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "Assalomu alaykum! Reklama va aksiyalar botiga xush kelibsiz.\nBo'limni tanlang:"
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(msg, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "main_menu":
        await start(update, context)

    elif data == "menu_categories":
        keyboard = [
            [InlineKeyboardButton("👕 Tekstil va Kiyimlar", callback_data="view_tekstil")],
            [InlineKeyboardButton("📱 Texnika va Gadjetlar", callback_data="view_texnika")],
            [InlineKeyboardButton("🍕 Oziq-ovqat va Restoran", callback_data="view_ovqat")],
            [InlineKeyboardButton("⬅️ Ortga", callback_data="main_menu")]
        ]
        await query.message.edit_text("Qaysi bo'limdagi reklamalarni ko'rmoqchisiz?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("view_"):
        category = data.split("_")[1]
        current_time = time.time()
        
        if user_id in user_cooldowns:
            passed_time = current_time - user_cooldowns[user_id]
            if passed_time < 60:
                wait_time = int(60 - passed_time)
                await query.answer(f"⏳ Boshqa reklama ko'rish uchun {wait_time} soniya kuting!", show_alert=True)
                return

        ads = ads_database.get(category, [])
        if not ads:
            await query.answer("Hozircha bu bo'limda reklama yo'q!", show_alert=True)
            return

        selected_ad = random.choice(ads)
        selected_ad["views"] += 1
        user_cooldowns[user_id] = current_time

        keyboard = [
            [
                InlineKeyboardButton(f"❤️ Like ({selected_ad['likes']})", callback_data=f"like_{category}_{selected_ad['id']}"),
                InlineKeyboardButton("🔗 Saytga o'tish", url=selected_ad["link"])
            ],
            [InlineKeyboardButton("🔄 Boshqa reklama ko'rish", callback_data=f"view_{category}")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="main_menu")]
        ]
        
        ad_text = f"<b>{selected_ad['text']}</b>\n\n👁 Ko'rishlar soni: {selected_ad['views']}"
        await query.message.edit_text(ad_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("like_"):
        _, category, ad_id = data.split("_")
        ad_id = int(ad_id)
        for ad in ads_database[category]:
            if ad["id"] == ad_id:
                ad["likes"] += 1
                await query.answer("Rahmat! Likingiz hisobga olindi.", show_alert=True)
                break

    elif data == "my_ads":
        text = "📊 <b>Sizning aktiv reklamalaringiz statistikasi:</b>\n\n"
        for cat, ads in ads_database.items():
            for ad in ads:
                text += f"📌 <b>Reklama:</b> {ad['text']}\n"
                text += f"👁 Ko'rishlar: <b>{ad['views']}</b> ta | ❤️ Like'lar: <b>{ad['likes']}</b> ta\n"
                text += "-------------------------\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Ortga", callback_data="main_menu")]]
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_ad_info":
        text = (
            "📢 <b>Reklama joylashtirish uchun:</b>\n\n"
            "1. Reklamangiz turiga qarab bo'limni tanlang.\n"
            "2. To'lovni amalga oshiring (100,000 so'm / 1 oy).\n"
            "3. Admin bilan bog'lanib postni tasdiqlating.\n\n"
            "👨‍💻 <b>Admin aloqa:</b> @admin_profi"
        )
        keyboard = [[InlineKeyboardButton("⬅️️ Ortga", callback_data="main_menu")]]
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    # Veb-serverni alohida oqimda (thread) ishga tushiramiz
    threading.Thread(target=run_http_server, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
