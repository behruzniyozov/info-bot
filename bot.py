import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from models import init_db, save_user, get_user_language, save_message, save_message_mapping, get_user_from_message, get_all_user_ids
from logger import logger, log_user_action, log_message, log_error, log_bot_start

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
_channel = os.getenv("CHANNEL_USERNAME")
# Convert to int if it's a numeric ID (for private channels)
CHANNEL_USERNAME = int(_channel) if _channel and _channel.lstrip('-').isdigit() else _channel

# Language display names
LANG_NAMES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English"
}

# Confirmation messages in different languages
CONFIRM_MESSAGES = {
    "uz": "✅ Xabaringiz yuborildi! Iltimos, javobni kuting.",
    "ru": "✅ Ваше сообщение отправлено! Пожалуйста, ожидайте ответа.",
    "en": "✅ Your message has been sent! Please wait for a response."
}

# Owner reply messages in different languages
OWNER_REPLY_MESSAGES = {
    "uz": "📨 Bot egasi javob berdi:",
    "ru": "📨 Владелец бота ответил:",
    "en": "📨 Bot owner replied:"
}

# News header messages in different languages
NEWS_HEADER = {
    "uz": "📢 Yangilik:",
    "ru": "📢 Новость:",
    "en": "📢 News:"
}

# Store pending news state
pending_news = {}

# Store pending post state
pending_post = {}

# Store currency conversion state: {user_id: {"from": "USD", "to": "UZS", "step": "amount"}}
currency_state = {}

# Currency labels
CURRENCY_LABELS = {
    "uz": {
        "title": "💱 Valyuta konvertori",
        "select_from": "Qaysi valyutadan:",
        "select_to": "Qaysi valyutaga:",
        "enter_amount": "Miqdorni kiriting:",
        "result": "Natija",
        "cancel": "❌ Bekor qilish",
        "convert_again": "🔄 Yana konvertatsiya",
        "invalid_number": "❌ Noto'g'ri son. Qaytadan kiriting."
    },
    "ru": {
        "title": "💱 Конвертер валют",
        "select_from": "Из какой валюты:",
        "select_to": "В какую валюту:",
        "enter_amount": "Введите сумму:",
        "result": "Результат",
        "cancel": "❌ Отмена",
        "convert_again": "🔄 Конвертировать снова",
        "invalid_number": "❌ Неверное число. Попробуйте снова."
    },
    "en": {
        "title": "💱 Currency Converter",
        "select_from": "From which currency:",
        "select_to": "To which currency:",
        "enter_amount": "Enter amount:",
        "result": "Result",
        "cancel": "❌ Cancel",
        "convert_again": "🔄 Convert again",
        "invalid_number": "❌ Invalid number. Please try again."
    }
}

# Currency flags
CURRENCY_FLAGS = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
    "UZS": "🇺🇿"
}

# Welcome message (shown before language selection)
WELCOME_MESSAGE = (
    "👋 Assalomu alaykum! / Здравствуйте! / Hello!\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🤖 Bu bot orqali siz:\n"
    "    • Bot egasiga xabar yuborishingiz\n"
    "    • Yangiliklar olishingiz\n"
    "    • /currency - 💱 Valyuta konvertatsiya\n\n"
    "🤖 С помощью этого бота вы можете:\n"
    "    • Отправить сообщение владельцу\n"
    "    • Получать новости\n"
    "    • /currency - 💱 Конвертер валют\n\n"
    "🤖 With this bot you can:\n"
    "    • Send message to the owner\n"
    "    • Receive news\n"
    "    • /currency - 💱 Currency converter\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🌐 Tilni tanlang / Выберите язык / Choose language:"
)

# Info messages in different languages
INFO_MESSAGES = {
    "uz": (
        "👤 Egasi: Qo'zimurodov Abduvali Utkirovich\n"
        "🛠 Yaratuvchi: @Behruz_Niyozov\n\n"
        "📊 Trading va ingliz tili bo'yicha bilimga ega shaxs\n\n"
        "📢 Kanalim: t.me/qozimurodovvv\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✉️ Sizning xabaringiz to'g'ridan-to'g'ri Bot egasiga yuboriladi.\n\n"
        "💬 Iltimos, savolingiz yoki so'rovingizni yozing — tez orada javob olasiz!\n\n"
        "📌 Buyruqlar:\n"
        "/currency - Valyuta konvertori"
    ),
    "ru": (
        "👤 Владелец: Козимуродов Абдували Уткирович\n"
        "🛠 Создатель: @Behruz_Niyozov\n\n"
        "📊 Специалист по трейдингу и английскому языку\n\n"
        "📢 Мой канал: t.me/qozimurodovvv\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✉️ Ваше сообщение будет отправлено напрямую владельцу бота.\n\n"
        "💬 Пожалуйста, напишите ваш вопрос или запрос — ответ придёт в ближайшее время!\n\n"
        "📌 Команды:\n"
        "/currency - Конвертер валют"
    ),
    "en": (
        "👤 Owner: Qozimurodov Abduvali Utkirovich\n"
        "🛠 Creator: @Behruz_Niyozov\n\n"
        "📊 Knowledgeable in Trading and English language\n\n"
        "📢 My channel: t.me/qozimurodovvv\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✉️ Your message will be sent directly to the bot owner.\n\n"
        "💬 Please feel free to send your question or request — you'll receive a reply soon!\n\n"
        "📌 Commands:\n"
        "/currency - Currency converter"
    )
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user

    if user.id == OWNER_ID:
        await update.message.reply_text(
            "Welcome, Owner! You will receive messages from users here.\n"
            "Reply to any forwarded message to respond to that user.\n\n"
            "📌 Commands:\n"
            "/news - Send news to all users\n"
            "/post - Send post to channel"
        )
        log_user_action(user.id, user.username, user.full_name, "START", "Owner started bot")
    else:
        keyboard = [
            [
                InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            WELCOME_MESSAGE,
            reply_markup=reply_markup
        )
        log_user_action(user.id, user.username, user.full_name, "START", "User started bot")


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback"""
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")
    user = query.from_user

    # Store user's language preference in database
    save_user(user.id, user.username, user.full_name, lang)
    log_user_action(user.id, user.username, user.full_name, "LANGUAGE_SELECT", f"Selected: {lang}")

    info_text = INFO_MESSAGES.get(lang, INFO_MESSAGES["en"])
    await query.edit_message_text(text=info_text)


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command - only for owner"""
    user = update.effective_user

    if user.id != OWNER_ID:
        return

    # Check if news text is provided with command
    if context.args:
        news_text = " ".join(context.args)
        await broadcast_news(context, news_text)
        await update.message.reply_text(
            f"📢 Yangilik yuborilmoqda...\n\n"
            f"Matn: {news_text}"
        )
    else:
        # Ask owner to send news
        pending_news[user.id] = True
        await update.message.reply_text(
            "📝 Iltimos, yangilik matnini yuboring:\n\n"
            "(Bekor qilish uchun /cancel)"
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user = update.effective_user

    if user.id == OWNER_ID:
        cancelled = False
        if user.id in pending_news:
            del pending_news[user.id]
            cancelled = True
        if user.id in pending_post:
            del pending_post[user.id]
            cancelled = True
        if cancelled:
            await update.message.reply_text("❌ Bekor qilindi / Cancelled")


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /post command - send post to channel (owner only)"""
    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if not CHANNEL_USERNAME:
        await update.message.reply_text("❌ CHANNEL_USERNAME not set in .env")
        return

    # Check if post text is provided with command
    if context.args:
        post_text = " ".join(context.args)
        await send_to_channel(context, post_text, update)
    else:
        pending_post[user.id] = True
        await update.message.reply_text(
            "📝 Post matnini yuboring:\n\n"
            "(Bekor qilish uchun /cancel)"
        )


async def send_to_channel(context: ContextTypes.DEFAULT_TYPE, text: str = None, update: Update = None, message = None):
    """Send a post to the channel (text or media)"""
    try:
        if message and (message.photo or message.video or message.document or message.audio or message.voice):
            # Copy media message to channel
            await message.copy(chat_id=CHANNEL_USERNAME)
            if update:
                await update.message.reply_text(f"✅ Post kanalga yuborildi!\n\n📢 {CHANNEL_USERNAME}")
            log_user_action(OWNER_ID, None, "Owner", "CHANNEL_POST", f"Media posted to {CHANNEL_USERNAME}")
        elif text:
            # Send text message
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=text,
                parse_mode="HTML"
            )
            if update:
                await update.message.reply_text(f"✅ Post kanalga yuborildi!\n\n📢 {CHANNEL_USERNAME}")
            log_user_action(OWNER_ID, None, "Owner", "CHANNEL_POST", f"Posted to {CHANNEL_USERNAME}")
    except Exception as e:
        error_msg = f"❌ Kanalga yuborishda xatolik: {e}"
        if update:
            await update.message.reply_text(error_msg)
        log_error(str(e), "Channel post failed")


async def get_exchange_rates():
    """Fetch exchange rates from API (base: UZS)"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get rates from CBU (Central Bank of Uzbekistan)
            url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    rates = {}
                    for item in data:
                        if item['Ccy'] in ['USD', 'EUR', 'RUB']:
                            rates[item['Ccy']] = {
                                'rate': float(item['Rate']),
                                'diff': item['Diff']
                            }
                    return rates
    except Exception as e:
        log_error(str(e), "Failed to fetch exchange rates")
    return None


async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /currency command - Step 1: Select FROM currency"""
    user = update.effective_user
    user_lang = get_user_language(user.id)
    labels = CURRENCY_LABELS.get(user_lang, CURRENCY_LABELS["en"])

    keyboard = [
        [
            InlineKeyboardButton(f"{CURRENCY_FLAGS['USD']} USD", callback_data="cfrom_USD"),
            InlineKeyboardButton(f"{CURRENCY_FLAGS['EUR']} EUR", callback_data="cfrom_EUR"),
        ],
        [
            InlineKeyboardButton(f"{CURRENCY_FLAGS['RUB']} RUB", callback_data="cfrom_RUB"),
            InlineKeyboardButton(f"{CURRENCY_FLAGS['UZS']} UZS", callback_data="cfrom_UZS"),
        ],
        [InlineKeyboardButton(labels['cancel'], callback_data="currency_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{labels['title']}\n\n{labels['select_from']}",
        reply_markup=reply_markup
    )

    log_user_action(user.id, user.username, user.full_name, "CURRENCY", "Started currency conversion")


async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency selection callbacks"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_lang = get_user_language(user.id)
    labels = CURRENCY_LABELS.get(user_lang, CURRENCY_LABELS["en"])

    data = query.data

    # Cancel
    if data == "currency_cancel":
        if user.id in currency_state:
            del currency_state[user.id]
        await query.edit_message_text("❌ Bekor qilindi / Отменено / Cancelled")
        return

    # Restart conversion
    if data == "currency_restart":
        keyboard = [
            [
                InlineKeyboardButton(f"{CURRENCY_FLAGS['USD']} USD", callback_data="cfrom_USD"),
                InlineKeyboardButton(f"{CURRENCY_FLAGS['EUR']} EUR", callback_data="cfrom_EUR"),
            ],
            [
                InlineKeyboardButton(f"{CURRENCY_FLAGS['RUB']} RUB", callback_data="cfrom_RUB"),
                InlineKeyboardButton(f"{CURRENCY_FLAGS['UZS']} UZS", callback_data="cfrom_UZS"),
            ],
            [InlineKeyboardButton(labels['cancel'], callback_data="currency_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"{labels['title']}\n\n{labels['select_from']}",
            reply_markup=reply_markup
        )
        return

    # Step 1: FROM currency selected
    if data.startswith("cfrom_"):
        from_currency = data.replace("cfrom_", "")
        currency_state[user.id] = {"from": from_currency, "step": "to"}

        # Show TO currency buttons (exclude the FROM currency)
        currencies = ["USD", "EUR", "RUB", "UZS"]
        currencies.remove(from_currency)

        keyboard = []
        row = []
        for ccy in currencies:
            row.append(InlineKeyboardButton(f"{CURRENCY_FLAGS[ccy]} {ccy}", callback_data=f"cto_{ccy}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton(labels['cancel'], callback_data="currency_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"{labels['title']}\n\n"
            f"{CURRENCY_FLAGS[from_currency]} {from_currency} ➡️ ?\n\n"
            f"{labels['select_to']}",
            reply_markup=reply_markup
        )
        return

    # Step 2: TO currency selected
    if data.startswith("cto_"):
        to_currency = data.replace("cto_", "")

        if user.id not in currency_state:
            await query.edit_message_text("❌ Xatolik. Qaytadan /currency bosing.")
            return

        currency_state[user.id]["to"] = to_currency
        currency_state[user.id]["step"] = "amount"

        from_currency = currency_state[user.id]["from"]

        keyboard = [[InlineKeyboardButton(labels['cancel'], callback_data="currency_cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"{labels['title']}\n\n"
            f"{CURRENCY_FLAGS[from_currency]} {from_currency} ➡️ {CURRENCY_FLAGS[to_currency]} {to_currency}\n\n"
            f"{labels['enter_amount']}",
            reply_markup=reply_markup
        )
        return


async def convert_currency(amount: float, from_ccy: str, to_ccy: str, rates: dict) -> float:
    """Convert currency amount"""
    # All rates are relative to UZS
    if from_ccy == "UZS":
        from_rate = 1
    else:
        from_rate = rates.get(from_ccy, {}).get('rate', 1)

    if to_ccy == "UZS":
        to_rate = 1
    else:
        to_rate = rates.get(to_ccy, {}).get('rate', 1)

    # Convert: amount in from_ccy -> UZS -> to_ccy
    uzs_amount = amount * from_rate
    result = uzs_amount / to_rate

    return result


async def broadcast_news(context: ContextTypes.DEFAULT_TYPE, news_text: str = None, media_message = None):
    """Broadcast news to all users (text or media)"""
    user_ids = get_all_user_ids()
    success_count = 0
    fail_count = 0

    for user_id in user_ids:
        try:
            user_lang = get_user_language(user_id)
            header = NEWS_HEADER.get(user_lang, NEWS_HEADER["en"])

            if media_message:
                # Send header first
                await context.bot.send_message(
                    chat_id=user_id,
                    text=header,
                    parse_mode="HTML"
                )
                # Then copy the media
                await media_message.copy(chat_id=user_id)
            else:
                message = f'{header}\n\n<b>"{news_text}"</b>'
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML"
                )
            success_count += 1
        except Exception as e:
            fail_count += 1
            log_error(str(e), f"Failed to send news to user {user_id}")

    # Notify owner about broadcast result
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"✅ Yangilik yuborildi!\n\n"
             f"📊 Natija:\n"
             f"✓ Yuborildi: {success_count}\n"
             f"✗ Xatolik: {fail_count}"
    )

    log_user_action(OWNER_ID, None, "Owner", "BROADCAST_NEWS", f"Success: {success_count}, Failed: {fail_count}")


async def handle_currency_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency amount input"""
    user = update.effective_user
    message = update.message
    user_lang = get_user_language(user.id)
    labels = CURRENCY_LABELS.get(user_lang, CURRENCY_LABELS["en"])

    state = currency_state.get(user.id)
    if not state:
        return

    # Parse amount
    try:
        amount_text = message.text.replace(",", ".").replace(" ", "")
        amount = float(amount_text)
    except ValueError:
        await message.reply_text(labels['invalid_number'])
        return

    from_ccy = state["from"]
    to_ccy = state["to"]

    # Get rates and convert
    rates = await get_exchange_rates()
    if not rates:
        await message.reply_text("❌ Valyuta kurslarini olishda xatolik.")
        del currency_state[user.id]
        return

    result = await convert_currency(amount, from_ccy, to_ccy, rates)

    # Clear state
    del currency_state[user.id]

    # Format result
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = (
        f"{labels['title']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{CURRENCY_FLAGS[from_ccy]} <b>{amount:,.2f} {from_ccy}</b>\n\n"
        f"⬇️\n\n"
        f"{CURRENCY_FLAGS[to_ccy]} <b>{result:,.2f} {to_ccy}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {now}"
    )

    # Add "Convert again" button
    keyboard = [[InlineKeyboardButton(labels['convert_again'], callback_data="currency_restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

    log_user_action(user.id, user.username, user.full_name, "CURRENCY_CONVERT", f"{amount} {from_ccy} -> {result:.2f} {to_ccy}")


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user messages to owner"""
    user = update.effective_user
    message = update.message

    # Check if user is entering currency amount
    if user.id in currency_state and currency_state[user.id].get("step") == "amount":
        await handle_currency_amount(update, context)
        return

    if user.id == OWNER_ID:
        # Check if owner is sending news
        if user.id in pending_news:
            del pending_news[user.id]
            await broadcast_news(context, message.text)
            return

        # Check if owner is sending channel post
        if user.id in pending_post:
            del pending_post[user.id]
            await send_to_channel(context, message.text, update)
            return

        # Owner is replying to a user
        target_user_id = None
        if message.reply_to_message:
            target_user_id = get_user_from_message(message.reply_to_message.message_id)

        if target_user_id:
            try:
                # Get user's language preference
                target_user_lang = get_user_language(target_user_id)
                reply_header = OWNER_REPLY_MESSAGES.get(target_user_lang, OWNER_REPLY_MESSAGES["en"])

                reply_text = f'{reply_header}\n<b>"{message.text}"</b>'

                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=reply_text,
                    parse_mode="HTML"
                )
                await message.reply_text("✅ Message sent!")

                # Log and save outgoing message
                save_message(target_user_id, message.text, "text", "outgoing")
                log_message(target_user_id, "outgoing", "text", message.text)
            except Exception as e:
                await message.reply_text(f"❌ Failed to send message: {e}")
                log_error(str(e), "Owner reply failed")
        else:
            await message.reply_text("Reply to a user's message to respond to them.")
    else:
        # Save user info
        save_user(user.id, user.username, user.full_name)

        # User sending message to owner
        username = f"@{user.username}" if user.username else "None"
        user_lang = get_user_language(user.id)
        lang_display = LANG_NAMES.get(user_lang, "🇬🇧 English")

        user_info = (
            f"📩 New Message\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 From: {user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: {user.id}\n"
            f"🌐 Language: {lang_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f'💬 Message:\n<b>"{message.text}"</b>'
        )

        forwarded = await context.bot.send_message(
            chat_id=OWNER_ID,
            text=user_info,
            parse_mode="HTML"
        )

        # Store mapping for reply in database
        save_message_mapping(forwarded.message_id, user.id)

        # Log and save incoming message
        save_message(user.id, message.text, "text", "incoming")
        log_message(user.id, "incoming", "text", message.text)

        confirm_msg = CONFIRM_MESSAGES.get(user_lang, CONFIRM_MESSAGES["en"])
        await message.reply_text(confirm_msg)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media messages (photos, documents, etc.)"""
    user = update.effective_user
    message = update.message

    # Determine media type
    if message.photo:
        media_type = "photo"
    elif message.video:
        media_type = "video"
    elif message.audio:
        media_type = "audio"
    elif message.voice:
        media_type = "voice"
    elif message.document:
        media_type = "document"
    else:
        media_type = "media"

    if user.id == OWNER_ID:
        logger.info(f"Owner sent media. pending_news: {user.id in pending_news}, pending_post: {user.id in pending_post}")

        # Check if owner is sending news with media
        if user.id in pending_news:
            del pending_news[user.id]
            await broadcast_news(context, media_message=message)
            await message.reply_text(
                f"✅ Yangilik yuborildi!\n\n"
                f"📊 Media broadcast completed"
            )
            return

        # Check if owner is sending channel post with media
        if user.id in pending_post:
            del pending_post[user.id]
            try:
                await message.copy(chat_id=CHANNEL_USERNAME)
                await message.reply_text(f"✅ Post kanalga yuborildi!\n\n📢 {CHANNEL_USERNAME}")
                log_user_action(OWNER_ID, None, "Owner", "CHANNEL_POST", f"Media posted to {CHANNEL_USERNAME}")
            except Exception as e:
                await message.reply_text(f"❌ Kanalga yuborishda xatolik: {e}")
                log_error(str(e), "Channel media post failed")
            return

        # Owner replying with media
        target_user_id = None
        if message.reply_to_message:
            target_user_id = get_user_from_message(message.reply_to_message.message_id)

        if target_user_id:
            try:
                await message.copy(chat_id=target_user_id)
                await message.reply_text("Media sent!")

                # Log outgoing media
                save_message(target_user_id, f"[{media_type}]", media_type, "outgoing")
                log_message(target_user_id, "outgoing", media_type)
            except Exception as e:
                await message.reply_text(f"Failed to send media: {e}")
                log_error(str(e), "Owner media reply failed")
        else:
            await message.reply_text("Reply to a user's message to respond to them.")
    else:
        # Save user info
        save_user(user.id, user.username, user.full_name)

        # User sending media to owner
        username = f"@{user.username}" if user.username else "None"
        user_lang = get_user_language(user.id)
        lang_display = LANG_NAMES.get(user_lang, "🇬🇧 English")

        user_info = (
            f"📩 New Media\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 From: {user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: {user.id}\n"
            f"🌐 Language: {lang_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

        # Send user info first
        info_msg = await context.bot.send_message(chat_id=OWNER_ID, text=user_info)

        # Forward the media
        forwarded = await message.copy(chat_id=OWNER_ID)

        # Store mappings in database
        save_message_mapping(info_msg.message_id, user.id)
        save_message_mapping(forwarded.message_id, user.id)

        # Log and save incoming media
        caption = message.caption or ""
        save_message(user.id, f"[{media_type}] {caption}", media_type, "incoming")
        log_message(user.id, "incoming", media_type, caption)

        confirm_msg = CONFIRM_MESSAGES.get(user_lang, CONFIRM_MESSAGES["en"])
        await message.reply_text(confirm_msg)


async def main():
    """Start the bot"""
    # Initialize database
    init_db()
    log_bot_start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("currency", currency_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(currency_callback, pattern="^(currency_|cfrom_|cto_)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.VOICE,
        handle_media
    ))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
