from logging import error, exception
from os import getenv
from dotenv import load_dotenv
from telegram.ext import CommandHandler, ContextTypes, filters
from telegram import Update

import admin
import client

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
    if update.message.chat.id == ADMIN_ID: 
        await admin.start(update, context)
    else:
        await client.start(update, context)



app.add_handler(CommandHandler('start', start));

admin.register_handlers(app)
client.register_handlers(app)

app.run_polling()
