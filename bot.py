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
user_balances = {}  # user_id: rekcoin_amount

ads_database = {
    "👕 Tekstil va Kiyimlar": [
        {"id": 1, "text": "👕 Uzum Marketda kiyim-kechaklarga 50% chegirma!", "link": "https://uzum.uz", "views": 0, "likes": set()}
    ],
    "📱 Texnika va Gadjetlar": [
        {"id": 2, "text": "📱 Arzon iPhone va maishiy texnika do'koni!", "link": "https://uzum.uz", "views": 0, "likes": set()}
    ],
    "🍕 Oziq-ovqat va Restoran": [
        {"id": 3, "text": "🍕 Yevropa taomlari va fast-fud yetkazib berish xizmati!", "link": "https://uzum.uz", "views": 0, "likes": set()}
    ]
}

# Pastki klaviatura menyulari
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛍 Do'konlar va Aksiyalar")],
        [KeyboardButton("👤 Mening profilim"), KeyboardButton("📊 Mening reklamalarim")],
        [KeyboardButton("📢 Reklama joylashtirish")]
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
    user_id = update.message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0

    await update.message.reply_text(
        "Assalomu alaykum! Reklama va aksiyalar botiga xush kelibsiz.\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=MAIN_KEYBOARD
    )

# Matnli xabarlarga ishlov berish
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id not in user_balances:
        user_balances[user_id] = 0

    if text == "⬅️ Bosh menyu":
        await update.message.reply_text("Bosh menyudasiz:", reply_markup=MAIN_KEYBOARD)

    elif text == "🛍 Do'konlar va Aksiyalar":
        await update.message.reply_text("Qaysi bo'limdagi reklamalarni ko'rmoqchisiz?", reply_markup=CATEGORIES_KEYBOARD)

    elif text == "👤 Mening profilim":
        coins = user_balances.get(user_id, 0)
        msg = (
            f"👤 <b>Foydalanuvchi profili:</b>\n\n"
            f"💰 Balansingiz: <b>{coins} Rekcoin</b>\n\n"
            f"💡 <i>Har bir ko'rilgan reklama uchun 10 Rekcoin beriladi. 300 Rekcoin yig'ib, 1 soatlik tekin reklama joylashtirishingiz mumkin!</i>"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

    elif text in ads_database:
        current_time = time.time()
        
        # 5 soniyalik Taymer tekshiruvi
        if user_id in user_cooldowns:
            passed_time = current_time - user_cooldowns[user_id]
            if passed_time < 5:
                wait_time = int(5 - passed_time) + 1
                await update.message.reply_text(f"⏳ Boshqa reklama ko'rish uchun {wait_time} soniya kuting!")
                return

        ads = ads_database[text]
        if not ads:
            await update.message.reply_text("Hozircha bu bo'limda reklama yo'q!")
            return

        selected_ad = random.choice(ads)
        selected_ad["views"] += 1
        user_cooldowns[user_id] = current_time

        # 10 Rekcoin mukofot berish
        user_balances[user_id] += 10

        # Dynamic Like Button (Like / Unlike)
        has_liked = user_id in selected_ad["likes"]
        like_text = f"💔 Unlike ({len(selected_ad['likes'])})" if has_liked else f"❤️ Like ({len(selected_ad['likes'])})"

        inline_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(like_text, callback_data=f"like_{text}_{selected_ad['id']}"),
                InlineKeyboardButton("🔗 Saytga o'tish", url=selected_ad["link"])
            ]
        ])
        
        ad_text = (
            f"<b>{selected_ad['text']}</b>\n\n"
            f"👁 Ko'rishlar: {selected_ad['views']}\n"
            f"🎁 <i>+10 Rekcoin olindingiz! Balans: {user_balances[user_id]} Rekcoin</i>"
        )
        await update.message.reply_text(ad_text, parse_mode="HTML", reply_markup=inline_keyboard)

    elif text == "📊 Mening reklamalarim":
        msg = "📊 <b>Sizning aktiv reklamalaringiz statistikasi:</b>\n\n"
        for cat, ads in ads_database.items():
            for ad in ads:
                msg += f"📌 <b>Reklama:</b> {ad['text']}\n"
                msg += f"👁 Ko'rishlar: <b>{ad['views']}</b> ta | ❤️ Like'lar: <b>{len(ad['likes'])}</b> ta\n"
                msg += "-------------------------\n"
        await update.message.reply_text(msg, parse_mode="HTML")

    elif text == "📢 Reklama joylashtirish":
        coins = user_balances.get(user_id, 0)
        msg = (
            "📢 <b>Reklama joylashtirish Shartlari:</b>\n\n"
            "1. 💰 <b>Pullik reklama:</b> 100,000 so'm / 1 oy.\n"
            "2. 🎁 <b>Tekin reklama:</b> 300 Rekcoin evaziga 1 soat.\n\n"
            f"Sizning balansingiz: <b>{coins} Rekcoin</b>\n\n"
            "👨‍💻 <b>Admin aloqa:</b> @admin_profi"
        )
        inline_btn = []
        if coins >= 300:
            inline_btn.append([InlineKeyboardButton("🎁 300 Rekcoin'ga tekin reklama joylash", callback_data="claim_free_ad")])
        
        reply_markup = InlineKeyboardMarkup(inline_btn) if inline_btn else None
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

# Like / Unlike va Free Ad bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("like_"):
        _, category, ad_id = data.split("_")
        ad_id = int(ad_id)
        
        for ad in ads_database[category]:
            if ad["id"] == ad_id:
                if user_id in ad["likes"]:
                    ad["likes"].remove(user_id)
                    await query.answer("Likingiz olib tashlandi.", show_alert=True)
                else:
                    ad["likes"].add(user_id)
                    await query.answer("Rahmat! Likingiz hisobga olindi.", show_alert=True)

                has_liked = user_id in ad["likes"]
                like_text = f"💔 Unlike ({len(ad['likes'])})" if has_liked else f"❤️ Like ({len(ad['likes'])})"

                new_keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(like_text, callback_data=f"like_{category}_{ad['id']}"),
                        InlineKeyboardButton("🔗 Saytga o'tish", url=ad["link"])
                    ]
                ])
                await query.message.edit_reply_markup(reply_markup=new_keyboard)
                break

    elif data == "claim_free_ad":
        if user_balances.get(user_id, 0) >= 300:
            user_balances[user_id] -= 300
            await query.message.edit_text(
                "🎉 <b>300 Rekcoin yechildi!</b>\n\n"
                "1 soatlik tekin reklamangiz uchun matn va havolani admin'ga yuboring:\n"
                "👨‍💻 Admin: @admin_profi",
                parse_mode="HTML"
            )
        else:
            await query.answer("Rekcoin balansingiz yetarli emas!", show_alert=True)

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
