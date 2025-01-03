from logging import error
from os import getenv
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler  
from wallets import Wallets
from bookmakers import Bookmakers

from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters



load_dotenv()
try:
    ADMIN_ID = int(getenv("ADMIN_ID"))
except:
    error('Admin ID not provided in .env.')
    quit()


async def invalid_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Нет такого варианта ответа.")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=adminId , text="Res")


class Idle():
    @staticmethod
    async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Кошельки', 'Букмекеры']
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        await update.message.reply_text('Админ панель 👇', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Кошельки':
            context.user_data['state'] = Wallets

            await Wallets.pickAction(update, context)
        elif user_response == 'Букмекеры':
            context.user_data['state'] = Bookmakers

            await Bookmakers.pickAction(update, context)
        else:
            await invalid_reply(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if(context.user_data == None):
        return; 
    try: 
        state = context.user_data['state']
    except:        
        state = Idle
        context.user_data['state'] = state
    finally:
        await state.settings(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (context.user_data == None):
        return
    try: 
        state = context.user_data['state']
        await state.handle_reply(update, context)
    except:
        await invalid_reply(update, context)


def register_handlers(app: Application):     
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    app.add_handler(CommandHandler('settings', Idle.settings))
