from contextlib import contextmanager
from functools import update_wrapper
from logging import error, exception
from os import getenv, replace
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

async def getWallets():
    return wallets

async def addWallet(wallet):
    wallets.append(wallet)

async def deleteWallet(id):
    wallets.pop(id)


class EditWallet():
    pass

class DeleteWalletProcess():
    
    def __init__(self) -> None:
        self.step = 0

    @staticmethod
    async def walletNames() -> list[str]:
        wallets = await getWallets()
        list_of_names = list(map(lambda i: i['name'], wallets))
        return list_of_names

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:
    
        self.step += 1

        match self.step:
            case 1: 
                wallet_names = await DeleteWalletProcess.walletNames()
                reply = [wallet_names]

                reply.append(['Отмена'])
            
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите кошелек, который нужно удалить', reply_markup=markup)
                return False
            case _:
                wallet_names = await DeleteWalletProcess.walletNames()
                
                index = 0
                for i in wallet_names:

                    if user_response == i:
                        await deleteWallet(index)
                        return True

                    index += 1
 
                await invalid_reply(update, context)
                return True
               
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        await update.message.reply_text('Кошелек был удален!')


class AddWalletProcess():
    
    def __init__(self) -> None:
        self.step = 0

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:
        reply = [
                ['Отмена']
            ]
        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        
        self.step += 1
        
        #get response on previous question and ask actual
        match self.step: 
            case 1:
                await update.message.reply_text('Введите имя:', reply_markup=markup)
                return False
            case 2: 
                #get response for first question
                self.name = user_response

                await update.message.reply_text('Введите реквизиты:', reply_markup=markup)
                return False
            case _:
                self.details = user_response
                return True
       
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        await addWallet(
            { 
                "name": self.name,
                "details": self.details,
             }
        )
        await update.message.reply_text('Кошелек был добавлен!')
    

class Wallets():
    @staticmethod
    async def pickAction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Cписок кошельков'],
            ['Добавить кошелек', 'Удалить кошелек'],
            ['Изменить кошелек'],
            ['Отмена']
        ]

        markup = ReplyKeyboardMarkup(reply)
        await update.message.reply_text('Меню настройки кошельков', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['local_state'] = None
            state = Idle
            context.user_data['state'] = state
            await Idle.settings(update, context)

        elif user_response == 'Cписок кошельков':
            text = 'Список кошельков: '
            j = 0
            for i in await getWallets():
                j += 1
                text += '\n' + str(j) + '.' + i

            await update.message.reply_text(text)
            await Wallets.pickAction(update, context)

        elif user_response == 'Добавить кошелек':
            local_state = AddWalletProcess()
            context.user_data['local_state'] = local_state
            await local_state.run(update, context, None)
              
        elif user_response == 'Удалить кошелек':
            local_state = DeleteWalletProcess()
            context.user_data['local_state'] = local_state
            await local_state.run(update, context, None)

        elif user_response == 'Изменить кошелек':
            context.user_data['local_state'] = 0

        else:
            local_state = context.user_data['local_state']
            if local_state == None:
                await invalid_reply(update, context)
                return

            finish = await local_state.run(update, context, user_response) 
            if finish:
                await local_state.finalize(update, context)
                context.user_data['local_state'] = None
                await Wallets.pickAction(update, context)
                print(wallets)

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
