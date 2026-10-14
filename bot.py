import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8744941782:AAEh_QwqUvlzy3lF30bAEpJjQWQty_N9MKs"
DB_NAME = "funstat.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
