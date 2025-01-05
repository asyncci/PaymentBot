from io import UnsupportedOperation
from logging import error, exception
from os import getenv
from dotenv import load_dotenv
from telegram._utils.types import FileLike
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update

import admin, client

load_dotenv()

try:
    TOKEN = getenv("BOT_TOKEN")
except: 
    error('Token not provided in .env')
    quit()

try:
    ADMIN_ID = int(getenv("ADMIN_ID"))
except:
    error('Admin ID not provided in .env')
    quit()

from telegram.ext import ApplicationBuilder

app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    user = update.message.chat.id
    if user == ADMIN_ID: 
        await admin.start(update, context)
    else:
        if user in await admin.blockedUserIDs():
            text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите @igrokweb'
            await update.message.reply_text(text)
            return 

        await client.start(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.chat.id
    if user == ADMIN_ID: 
        await admin.handle_reply(update, context)
    else:
        if user in await admin.blockedUserIDs():
            text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите @igrokweb'
            await update.message.reply_text(text)
            return 
        
        await client.handle_reply(update, context)

app.add_handler(CommandHandler('start', start));
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_reply))

app.run_polling()
