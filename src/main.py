from os import getenv
from dotenv import load_dotenv
from telegram.ext import CommandHandler, ContextTypes, filters
from telegram import Update

import admin
import client

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
ADMIN_ID = int(getenv("ADMIN_ID"))

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
