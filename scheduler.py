"""
Reminder scheduler — checks every minute and sends notifications:
  • 1 day before the event
  • 30 minutes before
  • At the exact time
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from database import get_pending_reminders, mark_notified

logger = logging.getLogger(__name__)


async def check_reminders(bot: Bot):
    """Check all pending reminders and send notifications as needed."""
    now = datetime.now()
    reminders = get_pending_reminders()

    for r in reminders:
        remind_at = datetime.fromisoformat(r["remind_at"])
        user_id = r["user_id"]
        task = r["task"]
        rid = r["id"]
        formatted_time = remind_at.strftime("%d.%m.%Y %H:%M")

        # ── 1 kun oldin ──────────────────────────────────────────────────
        day_before = remind_at - timedelta(days=1)
        if not r["notified_day_before"] and now >= day_before:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🔔 *1 kun oldin eslatma!*\n\n"
                        f"📌 Vazifa: {task}\n"
                        f"📅 Vaqt: {formatted_time}\n\n"
                        f"Ertaga bu ishni unutmang!"
                    ),
                    parse_mode="Markdown"
                )
                mark_notified(rid, "notified_day_before")
                logger.info(f"[1 kun oldin] user={user_id} task='{task}'")
            except Exception as e:
                logger.error(f"Xato (1 kun oldin): {e}")

        # ── 30 daqiqa oldin ──────────────────────────────────────────────
        thirty_min_before = remind_at - timedelta(minutes=30)
        if not r["notified_30min"] and now >= thirty_min_before:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⚡ *30 daqiqada boshlanadi!*\n\n"
                        f"📌 Vazifa: {task}\n"
                        f"🕐 Vaqt: {formatted_time}\n\n"
                        f"Tayyorlaning!"
                    ),
                    parse_mode="Markdown"
                )
                mark_notified(rid, "notified_30min")
                logger.info(f"[30 daqiqa oldin] user={user_id} task='{task}'")
            except Exception as e:
                logger.error(f"Xato (30 daqiqa): {e}")

        # ── Aynan o'sha vaqt ─────────────────────────────────────────────
        if not r["notified_main"] and now >= remind_at:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🚨 *Vaqt keldi!*\n\n"
                        f"📌 {task}\n\n"
                        f"Muvaffaqiyat! ✅"
                    ),
                    parse_mode="Markdown"
                )
                mark_notified(rid, "notified_main")
                logger.info(f"[Asosiy] user={user_id} task='{task}'")
            except Exception as e:
                logger.error(f"Xato (asosiy): {e}")


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Start the background scheduler."""
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(
        check_reminders,
        trigger="interval",
        minutes=1,
        args=[bot],
        id="reminder_checker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler ishga tushdi ✅")
    return scheduler
