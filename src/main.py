from os import getenv
from dotenv import load_dotenv
from telegram.ext import CommandHandler, ContextTypes, filters
from telegram import Update

import admin
import client

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

from telegram.ext import ApplicationBuilder
 

app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    adminUserID = 1529101740
    
    if update.message.chat.id == adminUserID: 
        await admin.start(update, context)
    else:
        await client.start(update, context)



app.add_handler(CommandHandler('start', start));

admin.register_handlers(app)
client.register_handlers(app)

app.run_polling()
