"""
MemoryBot — Shaxsiy xotira va eslatma boti
Main entry point
"""
import os
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from dotenv import load_dotenv

from database import (
    init_db,
    save_note,
    get_all_notes,
    delete_note,
    save_reminder,
    get_user_reminders,
    delete_reminder,
)
from ai_search import search_notes, parse_reminder_datetime
from scheduler import start_scheduler

load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Conversation states ──────────────────────────────────────────────────────
(
    SAVE_TITLE,
    SAVE_CONTENT,
    SEARCH_QUERY,
    REMIND_INPUT,
) = range(4)


# ─────────────────────────────────────────────────────────────────────────────
#  /start  &  /help
# ─────────────────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *MemoryBot ga xush kelibsiz!*\n\n"
        "Men sizning shaxsiy xotirangizman.\n"
        "Ma'lumot bering — men eslab qolaman. Kerak payt — topib beraman.\n\n"
        "📋 *Buyruqlar:*\n"
        "🗒 /save — Ma'lumot saqlash\n"
        "🔍 /find — Ma'lumot qidirish\n"
        "📂 /list — Barcha eslatmalar\n"
        "⏰ /remind — Eslatma qo'shish\n"
        "📅 /reminders — Eslatmalar ro'yxati\n"
        "❓ /help — Yordam\n\n"
        "Yoki menga oddiy xabar yozsangiz ham bo'ladi!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)


# ─────────────────────────────────────────────────────────────────────────────
#  SAVE note  (ConversationHandler)
# ─────────────────────────────────────────────────────────────────────────────

async def save_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Ma'lumot nomi (sarlavha) nima?*\n\n"
        "Masalan: `Python kursi`, `Doktor uchrashuvi`, `Loyiha g'oyasi`\n\n"
        "Bekor qilish: /cancel",
        parse_mode="Markdown"
    )
    return SAVE_TITLE


async def save_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["note_title"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Sarlavha: *{ctx.user_data['note_title']}*\n\n"
        "📄 Endi ma'lumotning mazmunini yozing:\n"
        "(Istalgancha uzun bo'lishi mumkin)",
        parse_mode="Markdown"
    )
    return SAVE_CONTENT


async def save_content(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    title = ctx.user_data.get("note_title", "Nomsiz")
    content = update.message.text.strip()
    user_id = update.effective_user.id

    note_id = save_note(user_id, title, content)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    await update.message.reply_text(
        f"💾 *Saqlandi!*\n\n"
        f"🆔 ID: `{note_id}`\n"
        f"📌 Sarlavha: *{title}*\n"
        f"📅 Vaqt: {now}\n\n"
        f"Kerak payt /find orqali topishingiz mumkin.",
        parse_mode="Markdown"
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
#  FIND  (ConversationHandler)
# ─────────────────────────────────────────────────────────────────────────────

async def find_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *Nima qidirmoqchisiz?*\n\n"
        "Masalan: `Python haqida eslatma`, `doktor`, `uchrashuv`\n\n"
        "Bekor qilish: /cancel",
        parse_mode="Markdown"
    )
    return SEARCH_QUERY


async def find_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    user_id = update.effective_user.id

    await update.message.reply_text("🔄 Qidirilmoqda...")

    notes = get_all_notes(user_id)
    result = search_notes(query, notes)

    await update.message.reply_text(
        f"🔍 *Natija:*\n\n{result}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
#  LIST notes
# ─────────────────────────────────────────────────────────────────────────────

async def list_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = get_all_notes(user_id)

    if not notes:
        await update.message.reply_text(
            "📂 Hozircha hech qanday ma'lumot saqlanmagan.\n"
            "/save orqali birinchi ma'lumotingizni kiriting!"
        )
        return

    text = f"📂 *Barcha ma'lumotlar ({len(notes)} ta):*\n\n"
    keyboard = []

    for note in notes[:20]:  # Max 20 ta ko'rsatiladi
        date = note["created_at"][:10]
        text += f"🆔 `{note['id']}` | 📌 *{note['title']}* | 📅 {date}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 #{note['id']} ni o'chirish",
                callback_data=f"del_note_{note['id']}"
            )
        ])

    if len(notes) > 20:
        text += f"\n_(Faqat oxirgi 20 ta ko'rsatildi)_"

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def delete_note_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    note_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id

    if delete_note(user_id, note_id):
        await query.edit_message_text(f"🗑 Ma'lumot #{note_id} o'chirildi.")
    else:
        await query.edit_message_text("❌ O'chirishda xato yuz berdi.")


# ─────────────────────────────────────────────────────────────────────────────
#  REMIND  (ConversationHandler)
# ─────────────────────────────────────────────────────────────────────────────

async def remind_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏰ *Eslatma qo'shish*\n\n"
        "Vazifa va vaqtni yozing. Masalan:\n"
        "• `Ertaga soat 14:00 da shifokor bilan uchrashuv`\n"
        "• `27 oktyabr soat 9:00 da taqdimot`\n"
        "• `Bugun kechqurun 20:00 da sport`\n\n"
        "Bekor qilish: /cancel",
        parse_mode="Markdown"
    )
    return REMIND_INPUT


async def remind_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    await update.message.reply_text("⏳ Vaqt aniqlanmoqda...")

    try:
        result = parse_reminder_datetime(text)

        if result.get("error"):
            await update.message.reply_text(
                f"❌ {result['error']}\n\nQayta urinib ko'ring yoki /cancel bosing.",
                parse_mode="Markdown"
            )
            return REMIND_INPUT

        task = result["task"]
        dt = datetime.fromisoformat(result["datetime"])
        rid = save_reminder(user_id, task, dt)

        formatted = dt.strftime("%d.%m.%Y %H:%M")
        await update.message.reply_text(
            f"✅ *Eslatma qo'shildi!*\n\n"
            f"🆔 ID: `{rid}`\n"
            f"📌 Vazifa: *{task}*\n"
            f"📅 Vaqt: {formatted}\n\n"
            f"📬 Sizga xabar yuboriladi:\n"
            f"  • 1 kun oldin\n"
            f"  • 30 daqiqa oldin\n"
            f"  • Aynan o'sha vaqtda",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Remind parse xato: {e}")
        await update.message.reply_text(
            "❌ Vaqtni aniqlab bo'lmadi. Iltimos aniqroq yozing.\n"
            "Masalan: `Ertaga soat 10:00 da uchrashuv`"
        )
        return REMIND_INPUT

    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
#  LIST reminders
# ─────────────────────────────────────────────────────────────────────────────

async def list_reminders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = get_user_reminders(user_id)

    if not reminders:
        await update.message.reply_text(
            "📅 Faol eslatmalar yo'q.\n"
            "/remind orqali yangi eslatma qo'shing!"
        )
        return

    text = f"📅 *Faol eslatmalar ({len(reminders)} ta):*\n\n"
    keyboard = []

    for r in reminders:
        dt = datetime.fromisoformat(r["remind_at"])
        formatted = dt.strftime("%d.%m.%Y %H:%M")
        text += f"🆔 `{r['id']}` | ⏰ {formatted}\n📌 {r['task']}\n\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 #{r['id']} ni bekor qilish",
                callback_data=f"del_remind_{r['id']}"
            )
        ])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def delete_reminder_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rid = int(query.data.split("_")[-1])
    user_id = update.effective_user.id

    if delete_reminder(user_id, rid):
        await query.edit_message_text(f"🗑 Eslatma #{rid} bekor qilindi.")
    else:
        await query.edit_message_text("❌ O'chirishda xato.")


# ─────────────────────────────────────────────────────────────────────────────
#  Fallback — oddiy xabar orqali qidirish
# ─────────────────────────────────────────────────────────────────────────────

async def free_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """If user sends a plain message, treat it as a search query."""
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if len(text) < 3:
        await update.message.reply_text(
            "❓ Nima qilishni bilmayapman.\n"
            "/help orqali buyruqlarni ko'ring."
        )
        return

    await update.message.reply_text("🔄 Qidirilmoqda...")
    notes = get_all_notes(user_id)
    result = search_notes(text, notes)
    await update.message.reply_text(f"🔍 *Natija:*\n\n{result}", parse_mode="Markdown")


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    init_db()
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    app = Application.builder().token(token).build()

    # Save conversation
    save_conv = ConversationHandler(
        entry_points=[CommandHandler("save", save_start)],
        states={
            SAVE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_title)],
            SAVE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Find conversation
    find_conv = ConversationHandler(
        entry_points=[CommandHandler("find", find_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_query)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Remind conversation
    remind_conv = ConversationHandler(
        entry_points=[CommandHandler("remind", remind_start)],
        states={
            REMIND_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("list", list_notes))
    app.add_handler(CommandHandler("reminders", list_reminders))
    app.add_handler(save_conv)
    app.add_handler(find_conv)
    app.add_handler(remind_conv)
    app.add_handler(CallbackQueryHandler(delete_note_callback, pattern=r"^del_note_"))
    app.add_handler(CallbackQueryHandler(delete_reminder_callback, pattern=r"^del_remind_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text))

    # Start scheduler
    bot = app.bot
    start_scheduler(bot)

    logger.info("MemoryBot ishga tushdi! 🚀")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
