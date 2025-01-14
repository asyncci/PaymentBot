from functools import update_wrapper
from io import UnsupportedOperation
from logging import error, exception
from os import getenv
import sys
from dotenv import load_dotenv
from telegram._utils.types import FileLike
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
import logging
import admin, client

load_dotenv()

orig_stdout = sys.stdout
f = open('out.txt', 'w')
sys.stdout = f

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

async def button_handler(update: Update, context: CallbackContext) -> None:
    await admin.button_handler(update, context)

#logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    #level=logging.DEBUG)

app.add_handler(CommandHandler('start', start));
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_reply))
app.add_handler(CallbackQueryHandler(button_handler))
app.run_polling()
