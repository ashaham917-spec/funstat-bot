import asyncio
import logging
import os
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

BOT_TOKEN = "8744941782:AAEh_QwqUvlzy3lF30bAEpJjQWQty_N9MKs"
DB_NAME = "funstat.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def handle_ping(request):
    return web.Response(text="Bot is alive and running!")

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users_data (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                detected_chats TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS hidden_targets (
                user_id INTEGER PRIMARY KEY
            );
        ''')
        await db.commit()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 فحص حساب / OSINT", callback_data="scan_user")],
        [InlineKeyboardButton(text="🛡 إخفاء بياناتي من الفحص", callback_data="hide_me")],
        [InlineKeyboardButton(text="📊 إحصائيات النظام", callback_data="system_stats")]
    ])
    await message.answer(
        "<b>نظام FunStat / OSINT Intelligence</b>\n\n"
        "أرسل معرف الهدف (User ID / Username) للبدء في تتبع وتحليل نشاطه.",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(F.data == "scan_user")
async def cb_scan(callback: types.CallbackQuery):
    await callback.message.answer("أرسل يوزرنيم أو ID الهدف الآن لبدء عمليات التحليل.")
    await callback.answer()

@dp.callback_query(F.data == "hide_me")
async def cb_hide(callback: types.CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO hidden_targets (user_id) VALUES (?)", 
            (callback.from_user.id,)
        )
        await db.commit()
    await callback.answer("تم إدراج معرفك في قائمة الحماية والإخفاء بنجاح.", show_alert=True)

@dp.callback_query(F.data == "system_stats")
async def cb_stats(callback: types.CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users_data") as cursor:
            users_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM hidden_targets") as cursor:
            hidden_count = (await cursor.fetchone())[0]
            
    await callback.message.answer(
        f"📊 <b>إحصائيات النظام التشغيلي:</b>\n\n"
        f"• الأهداف المسجلة: <code>{users_count}</code>\n"
        f"• الحسابات المحمية: <code>{hidden_count}</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(F.text & ~F.text.startswith("/"))
async def analyze_target(message: types.Message):
    target = message.text.replace("@", "").strip()
    status_msg = await message.answer("🔄 جاري الاتصال بقواعد البيانات وتحليل الهدف...")

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM hidden_targets WHERE user_id = ?", (message.from_user.id,)) as cursor:
            is_hidden = await cursor.fetchone()
            
        if is_hidden:
            await status_msg.edit_text("❌ هذا الحساب محمي بموجب نظام FunStat Hide.")
            return

        async with db.execute("SELECT * FROM users_data WHERE username = ? OR CAST(user_id AS TEXT) = ?", (target, target)) as cursor:
            row = await cursor.fetchone()

    if not row:
        await status_msg.edit_text(f"⚠️ لم يتم العثور على سجلات سابقة للهدف: <code>{target}</code> في قاعدة البيانات الحالية.", parse_mode="HTML")
        return

    chats_list = row[4] if row[4] else "لا توجد مجموعات مكشوفة حالياً"

    report = (
        f"<b>🎯 تقرير الاستخبارات والتحليل:</b>\n\n"
        f"👤 <b>ID:</b> <code>{row[0]}</code>\n"
        f"🏷 <b>الاسم:</b> {row[2]} {row[3] or ''}\n"
        f"🔗 <b>اليوزر:</b> @{row[1]}\n\n"
        f"🌐 <b>المجموعات والقنوات التابعة للهدف:</b>\n{chats_list}\n\n"
        f"🕒 <b>آخر ظهور مسجل:</b> {row[5]}"
    )
    await status_msg.edit_text(report, parse_mode="HTML")

async def main():
    await init_db()
    
    # إعداد وتشغيل خادم الويب ليطابق شروط المنصة المجانية
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started successfully on port {port}")
    
    print("ZYROS Bot System Active (SQLite + Web Server)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
