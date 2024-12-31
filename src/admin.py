from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler  

from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('GHel')


def register_handlers(app: Application):     
    #app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    pass
