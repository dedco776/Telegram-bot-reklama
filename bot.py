import os
import time
import random
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    ConversationHandler, filters, ContextTypes
)

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

# Conversation states
SELECT_CATEGORY, ENTER_TITLE, ENTER_DESCRIPTION, UPLOAD_PHOTO, ENTER_LINK = range(5)
ADD_COMMENT = 10

# Barcha Reklama Kategoriyalari
ads_database = {
    "📲 Ijtimoiy tarmoqlar": [],
    "👕 Kiyim va Go'zallik": [],
    "📱 Texnika va Gadjetlar": [],
    "🍕 Oziq-ovqat va Kafe": [],
    "🚗 Avto va Ko'chmas mulk": [],
    "🎓 Ta'lim va Ish o'rinlari": [],
    "🛠 Xizmatlar va Boshqalar": []
}

# Dastlabki sinov reklamasi
ads_database["📲 Ijtimoiy tarmoqlar"].append({
    "id": 1, 
    "category": "📲 Ijtimoiy tarmoqlar",
    "title": "YouTube kanalimizga obuna bo'ling!", 
    "text": "Eng yangi texnologiyalar va dasturlash bo'yicha video darsliklar.", 
    "link": "https://youtube.com", 
    "photo": None, 
    "views": 0, 
    "likes": set(),
    "comments": []  # [{"user": name, "text": comment}]
})

# Klaviatura menyulari
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛍 Do'konlar va Aksiyalar"), KeyboardButton("🎲 Tasodifiy reklama")],
        [KeyboardButton("👤 Mening profilim"), KeyboardButton("📊 Mening reklamalarim")],
        [KeyboardButton("📢 Reklama joylashtirish")]
    ],
    resize_keyboard=True
)

CATEGORIES_LIST = [
    [KeyboardButton("🎲 Tasodifiy reklama")],
    [KeyboardButton("📲 Ijtimoiy tarmoqlar"), KeyboardButton("👕 Kiyim va Go'zallik")],
    [KeyboardButton("📱 Texnika va Gadjetlar"), KeyboardButton("🍕 Oziq-ovqat va Kafe")],
    [KeyboardButton("🚗 Avto va Ko'chmas mulk"), KeyboardButton("🎓 Ta'lim va Ish o mebellari")],
    [KeyboardButton("🛠 Xizmatlar va Boshqalar")],
    [KeyboardButton("⬅️ Bosh menyu")]
]

CATEGORIES_KEYBOARD = ReplyKeyboardMarkup(CATEGORIES_LIST, resize_keyboard=True)

# Xabarlarni 5 daqiqadan so'ng avtomatik o'chirish
async def delete_message_later(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# Reklama Inline klaviaturasini shakllantirish
def build_ad_keyboard(category: str, ad: dict, user_id: int) -> InlineKeyboardMarkup:
    has_liked = user_id in ad["likes"]
    like_text = f"💔 Unlike ({len(ad['likes'])})" if has_liked else f"❤️ Like ({len(ad['likes'])})"
    comments_count = len(ad.get("comments", []))

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(like_text, callback_data=f"like_{category}_{ad['id']}"),
            InlineKeyboardButton(f"💬 Izohlar ({comments_count})", callback_data=f"comments_{category}_{ad['id']}")
        ],
        [
            InlineKeyboardButton("🔗 O'tish", url=ad["link"]),
            InlineKeyboardButton("⏩ Keyingi reklama", callback_data=f"next_{category}")
        ]
    ])
    return keyboard

# Start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0

    await update.message.reply_text(
        "Assalomu alaykum! Reklama va aksiyalar botiga xush kelibsiz.\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=MAIN_KEYBOARD
    )

# Reklamani ko'rsatish funksiyasi
async def show_ad(update_or_query, context: ContextTypes.DEFAULT_TYPE, category: str = None):
    if hasattr(update_or_query, 'message') and update_or_query.message:
        user_id = update_or_query.message.from_user.id
        chat_id = update_or_query.message.chat_id
    else:
        user_id = update_or_query.from_user.id
        chat_id = update_or_query.message.chat_id

    current_time = time.time()
    if user_id in user_cooldowns:
        passed_time = current_time - user_cooldowns[user_id]
        if passed_time < 5:
            wait_time = int(5 - passed_time) + 1
            msg_text = f"⏳ Boshqa reklama ko'rish uchun {wait_time} soniya kuting!"
            if hasattr(update_or_query, 'message') and update_or_query.message:
                await update_or_query.message.reply_text(msg_text)
            else:
                await update_or_query.answer(msg_text, show_alert=True)
            return

    # Reklamani tanlash
    if category == "random" or not category:
        all_ads = [ad for cat_ads in ads_database.values() for ad in cat_ads]
        if not all_ads:
            msg = "Hozircha hech qanday reklama mavjud emas!"
            if hasattr(update_or_query, 'message') and update_or_query.message:
                await update_or_query.message.reply_text(msg)
            else:
                await update_or_query.answer(msg, show_alert=True)
            return
        selected_ad = random.choice(all_ads)
        category = selected_ad["category"]
    else:
        ads = ads_database.get(category, [])
        if not ads:
            msg = "Hozircha bu bo'limda reklama yo'q!"
            if hasattr(update_or_query, 'message') and update_or_query.message:
                await update_or_query.message.reply_text(msg)
            else:
                await update_or_query.answer(msg, show_alert=True)
            return
        selected_ad = random.choice(ads)

    selected_ad["views"] += 1
    user_cooldowns[user_id] = current_time
    user_balances[user_id] = user_balances.get(user_id, 0) + 10

    reply_markup = build_ad_keyboard(category, selected_ad, user_id)
    ad_text = (
        f"📂 <b>[{category}]</b>\n"
        f"📌 <b>{selected_ad['title']}</b>\n\n"
        f"{selected_ad['text']}\n\n"
        f"👁 Ko'rishlar: {selected_ad['views']}\n"
        f"🎁 <i>+10 Rekcoin olindingiz! Balans: {user_balances[user_id]} Rekcoin</i>"
    )

    sent_msg = None
    if selected_ad.get("photo"):
        sent_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=selected_ad["photo"],
            caption=ad_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        sent_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=ad_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    # 5 daqiqa (300 sek) dan so'ng xabarni avtomatik o'chirish taymerini ishga tushirish
    if sent_msg:
        asyncio.create_task(delete_message_later(context, chat_id, sent_msg.message_id, 300))

# Matnli xabarlarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id not in user_balances:
        user_balances[user_id] = 0

    if text == "⬅️ Bosh menyu":
        await update.message.reply_text("Bosh menyudasiz:", reply_markup=MAIN_KEYBOARD)

    elif text == "🛍 Do'konlar va Aksiyalar":
        await update.message.reply_text("Qaysi bo'limdagi reklamalarni ko'rmoqchisiz?", reply_markup=CATEGORIES_KEYBOARD)

    elif text == "🎲 Tasodifiy reklama":
        await show_ad(update, context, category="random")

    elif text == "👤 Mening profilim":
        coins = user_balances.get(user_id, 0)
        msg = (
            f"👤 <b>Foydalanuvchi profili:</b>\n\n"
            f"💰 Balansingiz: <b>{coins} Rekcoin</b>\n\n"
            f"💡 <i>Har bir ko'rilgan reklama uchun 10 Rekcoin beriladi. 300 Rekcoin yig'ib, tekin reklama joylashtirishingiz mumkin!</i>"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

    elif text in ads_database:
        await show_ad(update, context, category=text)

    elif text == "📊 Mening reklamalarim":
        msg = "📊 <b>Aktiv reklamalar statistikasi:</b>\n\n"
        count = 0
        for cat, ads in ads_database.items():
            for ad in ads:
                count += 1
                msg += f"📌 <b>[{cat}]</b> {ad['title']}\n"
                msg += f"👁 Ko'rishlar: <b>{ad['views']}</b> | ❤️ Like: <b>{len(ad['likes'])}</b> | 💬 Izohlar: <b>{len(ad.get('comments', []))}</b>\n"
                msg += "-------------------------\n"
        if count == 0:
            msg = "Hozircha hech qanday reklama mavjud emas."
        await update.message.reply_text(msg, parse_mode="HTML")

    elif text == "📢 Reklama joylashtirish":
        coins = user_balances.get(user_id, 0)
        msg = (
            "📢 <b>Reklama joylashtirish shartlari:</b>\n\n"
            "1. 💰 <b>Pullik reklama:</b> Admin bilan bog'lanish (@admin_profi)\n"
            "2. 🎁 <b>Tekin reklama:</b> 300 Rekcoin evaziga bot ichida avtomatik joylash.\n\n"
            f"Sizning balansingiz: <b>{coins} Rekcoin</b>"
        )
        inline_btn = []
        if coins >= 300:
            inline_btn.append([InlineKeyboardButton("🎁 300 Rekcoin'ga tekin reklama joylash", callback_data="start_add_ad")])
        else:
            inline_btn.append([InlineKeyboardButton("❌ Rekcoin yetarli emas (Kamida 300 kerak)", callback_data="nocoin")])
        
        reply_markup = InlineKeyboardMarkup(inline_btn)
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

# Inline tugmalarni qayta ishlash
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "nocoin":
        await query.answer("Reklama joylash uchun kamida 300 Rekcoin yig'ishingiz kerak!", show_alert=True)
        return

    if data.startswith("next_"):
        category = data.split("_")[1]
        await query.answer()
        await show_ad(query, context, category=category)

    elif data.startswith("like_"):
        parts = data.split("_")
        category = parts[1]
        ad_id = int(parts[2])
        
        for ad in ads_database.get(category, []):
            if ad["id"] == ad_id:
                if user_id in ad["likes"]:
                    ad["likes"].remove(user_id)
                    await query.answer("Likingiz olib tashlandi.", show_alert=True)
                else:
                    ad["likes"].add(user_id)
                    await query.answer("Rahmat! Likingiz hisobga olindi.", show_alert=True)

                new_keyboard = build_ad_keyboard(category, ad, user_id)
                try:
                    await query.message.edit_reply_markup(reply_markup=new_keyboard)
                except:
                    pass
                break

    elif data.startswith("comments_"):
        parts = data.split("_")
        category = parts[1]
        ad_id = int(parts[2])

        for ad in ads_database.get(category, []):
            if ad["id"] == ad_id:
                comments = ad.get("comments", [])
                comm_msg = f"💬 <b>[{ad['title']}] uchun izohlar:</b>\n\n"
                if comments:
                    for c in comments:
                        comm_msg += f"👤 <b>{c['user']}:</b> {c['text']}\n"
                else:
                    comm_msg += "Hozircha hech qanday izoh yo'q.\n"

                comm_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ Izoh qoldirish", callback_data=f"writecomment_{category}_{ad_id}")]
                ])
                await query.message.reply_text(comm_msg, parse_mode="HTML", reply_markup=comm_keyboard)
                await query.answer()
                break

    elif data.startswith("writecomment_"):
        parts = data.split("_")
        context.user_data["comm_category"] = parts[1]
        context.user_data["comm_ad_id"] = int(parts[2])
        await query.message.reply_text("✏️ Reklama uchun izohingizni yozib yuboring:")
        await query.answer()
        return ADD_COMMENT

# Izoh yozish holati
async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment_text = update.message.text
    user_name = update.message.from_user.first_name
    category = context.user_data.get("comm_category")
    ad_id = context.user_data.get("comm_ad_id")

    for ad in ads_database.get(category, []):
        if ad["id"] == ad_id:
            if "comments" not in ad:
                ad["comments"] = []
            ad["comments"].append({"user": user_name, "text": comment_text})
            await update.message.reply_text("✅ Izohingiz muvaffaqiyatli qo'shildi!", reply_markup=MAIN_KEYBOARD)
            break

    return ConversationHandler.END

# --- REKLAMA JOYLASHTIRISH HANDLERS ---

async def start_add_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_balances.get(user_id, 0) < 300:
        await query.message.reply_text("Rekcoin balansingiz yetarli emas!")
        return ConversationHandler.END

    cat_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton(cat)] for cat in ads_database.keys()] + [[KeyboardButton("❌ Bekor qilish")]],
        resize_keyboard=True
    )
    await query.message.reply_text(
        "📂 Reklamangiz qaysi kategoriyaga (guruhga) tegishli? Tanlang:",
        reply_markup=cat_keyboard
    )
    return SELECT_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    if category == "❌ Bekor qilish":
        await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    if category not in ads_database:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang:")
        return SELECT_CATEGORY

    context.user_data['ad_category'] = category
    await update.message.reply_text("✏️ Reklamangiz sarlavhasini kiriting (Max 60 belgi):")
    return ENTER_TITLE

async def title_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    if title == "❌ Bekor qilish":
        await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    if len(title) > 60:
        await update.message.reply_text("❌ Sarlavha juda uzun! Maksimal 60 belgi bo'lishi kerak. Qaytadan kiriting:")
        return ENTER_TITLE

    context.user_data['ad_title'] = title
    await update.message.reply_text("📝 Reklama haqida batafsil matn yozing (Max 100 ta so'z):")
    return ENTER_DESCRIPTION

async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    if desc == "❌ Bekor qilish":
        await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    if len(desc.split()) > 100:
        await update.message.reply_text("❌ Matn juda uzun! Maksimal 100 ta so'z bo'lishi kerak. Qaytadan kiriting:")
        return ENTER_DESCRIPTION

    context.user_data['ad_description'] = desc
    photo_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("⏭ Rasmsiz davom etish")], [KeyboardButton("❌ Bekor qilish")]],
        resize_keyboard=True
    )
    await update.message.reply_text("🖼 Reklama uchun rasm yuboring (yoki 'Rasmsiz davom etish'ni bosing):", reply_markup=photo_keyboard)
    return UPLOAD_PHOTO

async def photo_uploaded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    if update.message.photo:
        context.user_data['ad_photo'] = update.message.photo[-1].file_id
    else:
        context.user_data['ad_photo'] = None

    await update.message.reply_text("🔗 Reklama uchun havolani (link) kiriting (http:// yoki https:// bilan):")
    return ENTER_LINK

async def link_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    if link == "❌ Bekor qilish":
        await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    if not (link.startswith("http://") or link.startswith("https://")):
        await update.message.reply_text("❌ Yaroqsiz havola! Link 'http://' yoki 'https://' bilan boshlanishi kerak:")
        return ENTER_LINK

    user_id = update.message.from_user.id
    user_balances[user_id] -= 300

    category = context.user_data['ad_category']
    new_ad = {
        "id": random.randint(1000, 9999),
        "category": category,
        "title": context.user_data['ad_title'],
        "text": context.user_data['ad_description'],
        "link": link,
        "photo": context.user_data.get('ad_photo'),
        "views": 0,
        "likes": set(),
        "comments": []
    }

    ads_database[category].append(new_ad)

    await update.message.reply_text(
        "🎉 <b>Tabriklaymiz! Reklamangiz muvaffaqiyatli joylashtirildi.</b>\n"
        "Balansingizdan 300 Rekcoin yechildi.",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END

async def cancel_add_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Amal bekor qilindi.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Reklama qo'shish uchun conversation
    add_ad_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_ad, pattern="^start_add_ad$")],
        states={
            SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category_selected)],
            ENTER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_entered)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_entered)],
            UPLOAD_PHOTO: [
                MessageHandler(filters.PHOTO, photo_uploaded),
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_uploaded)
            ],
            ENTER_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, link_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_ad)]
    )

    # Izoh yozish uchun conversation
    comment_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^writecomment_")],
        states={
            ADD_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_entered)]
        },
        fallbacks=[CommandHandler("cancel", cancel_add_ad)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_ad_handler)
    app.add_handler(comment_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
