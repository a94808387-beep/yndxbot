import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import BOT_TOKEN
from analyzer import load_report, analyze_placements, format_trash_report, get_placements_for_copy

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_results: dict = {}

WELCOME_TEXT = """\U0001F44B Привет! Я бот для анализа площадок РСЯ Яндекс.Директа.

\U0001F4CB Что я умею:
\U00002022 Анализировать отчёты из Яндекс.Директа
\U00002022 Выдавать готовый список для минус-площадок

\U0001F4E4 Как использовать:
1. Выгрузите отчёт по площадкам из Яндекс.Директа (Excel или CSV)
2. Отправьте файл мне
3. Получите список мусорных площадок
4. Скопируйте их в минус-площадки кампании

Отправьте мне файл с отчётом! \U0001F4CE
"""

SUPPORTED_EXTENSIONS = ('.xlsx', '.xls', '.csv')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    document = update.message.document
    file_name = document.file_name.lower()
    
    if not file_name.endswith(SUPPORTED_EXTENSIONS):
        await update.message.reply_text(
            "\u274C Неподдерживаемый формат файла.\n"
            "Отправьте файл в формате Excel (.xlsx, .xls) или CSV (.csv)"
        )
        return
    
    await update.message.reply_text("\u23F3 Загружаю и анализирую отчёт...")
    
    file = await context.bot.get_file(document.file_id)
    file_path = f"temp_{user_id}_{document.file_name}"
    
    try:
        await file.download_to_drive(file_path)
        
        df, status = load_report(file_path)
        if df is None:
            await update.message.reply_text(f"\u274C {status}")
            return
        
        trash_placements, status = analyze_placements(df)
        if status != "OK":
            await update.message.reply_text(f"\u274C {status}")
            return
        
        user_results[user_id] = trash_placements
        report = format_trash_report(trash_placements)
        
        keyboard = [[InlineKeyboardButton("\U0001F4CB Скопировать список", callback_data="copy_list")]] if trash_placements else []
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        if len(report) <= 4000:
            await update.message.reply_text(report, reply_markup=reply_markup)
        else:
            parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for i, part in enumerate(parts):
                markup = reply_markup if i == len(parts) - 1 else None
                await update.message.reply_text(part, reply_markup=markup)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    placements = user_results.get(user_id)
    
    if not placements:
        await query.edit_message_text("\u274C Данные устарели. Загрузите отчёт заново.")
        return
    
    if query.data == "copy_list":
        copy_text = get_placements_for_copy(placements)
        message = f"\U0001F4CB Список площадок для минус-площадок ({len(placements)} шт.):\n\n```\n{copy_text}\n```"
        
        if len(message) <= 4000:
            await query.message.reply_text(message, parse_mode='Markdown')
        else:
            await query.message.reply_text(f"Список площадок ({len(placements)} шт.):\n\nСписок большой, отправляю частями...")
            lines = copy_text.split('\n')
            chunk = []
            chunk_len = 0
            
            for line in lines:
                if chunk_len + len(line) > 3500:
                    await query.message.reply_text(f"```\n{chr(10).join(chunk)}\n```", parse_mode='Markdown')
                    chunk = []
                    chunk_len = 0
                chunk.append(line)
                chunk_len += len(line) + 1
            
            if chunk:
                await query.message.reply_text(f"```\n{chr(10).join(chunk)}\n```", parse_mode='Markdown')


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Ошибка: Укажите токен бота в .env файле")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
