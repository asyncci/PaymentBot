from logging import error, exception
from os import getenv
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler  

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


wallets = []


class EditWallet():


class AddWallet():
    @staticmethod
    async def add_wallet():
        pass

class ChangeWallets():
    @staticmethod
    async def pickAction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Добавить кошелек', 'Удалить кошелек'],
            ['Изменить кошелек']
        ]

        markup = ReplyKeyboardMarkup(reply)
        await update.message.reply_text('Что нужно изменить?', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Добавить кошелек':
            context.user_data['local_state'] = 'add'
            reply = [
                ['Отмена']
            ]
            markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
            await update.message.reply_text('Введите название:',reply_markup=markup)

        elif user_response == 'Удалить кошелек':
            context.user_data['local_state'] = 'delete'
            reply = [
                ([InlineKeyboardButton(x)] for x in wallets),
                [InlineKeyboardButton('Отмена')]
            ]

            await update.message.reply_text('Выберите кошелек:', reply_markup=markup)
            

        elif user_response == 'Изменить кошелек':
            context.user_data['staet']

        else:
            local_state = context.user_data['local_state']
            if local_state == None:
                await invalid_reply(update, context)
                return

            if local_state == 'add':
                wallets.append(user_response)
                await update.message.reply_text('Добавлен новый кошелек: {}'.format(user_response))
            

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
            context.user_data['state'] = ChangeWallets

            await ChangeWallets.pickAction(update, context)
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
    pass
