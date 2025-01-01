from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler  

from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

async def invalid_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Нет такого варианта ответа.")

def get_bookmakers() -> list[list[str]]:
    return [['X1Bet','Melbet', '1Win', 'Funpari']]

def get_wallets() -> list[list[str]]:
    return [['Mbank','Kompanion']]


class Withdraw(): 
    @staticmethod
    async def pick_bookmaker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = get_bookmakers()
        reply.append(['Отмена'])

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

        await update.message.reply_text('Выберите букмекер для вывода 👇', reply_markup=markup)
        

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['state'] = AgreedState
            await AgreedState.welcome(update, context)
        else:
            await invalid_reply(update, context)

class DepositWallet():
    @staticmethod
    async def pick_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = get_wallets()
        reply.append(['Отмена'])

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

        await update.message.reply_text('Выберите способ пополнения', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['state'] = AgreedState
            await AgreedState.welcome(update, context)
        else:
            if user_response not in get_wallets():
                await invalid_reply(update, context)
                return
            context.user_data['bookmaker'] = user_response
            context.user_data['state'] = DepositWallet
            await DepositWallet.pick_wallet(update, context)

class Deposit(): 
    @staticmethod
    async def pick_bookmaker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = get_bookmakers()
        reply.append(['Отмена'])

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

        await update.message.reply_text('Выберите букмекер 👇', reply_markup=markup)
        

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['state'] = AgreedState
            await AgreedState.welcome(update, context)
        else:
            if user_response not in get_bookmakers():
                await invalid_reply(update, context)
                return
            context.user_data['bookmaker'] = user_response
            context.user_data['state'] = DepositWallet
            await DepositWallet.pick_wallet(update, context)
            

class AgreedState():
    @staticmethod   
    async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = "Добро пожаловать в PayGo\n\n⚽️ Пополнение/Вывод: 0%\n⚡️ Моментальные пополнения\n"
    
        reply = [
            ['Пополнить', 'Вывести']
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

        await update.message.reply_text(text, reply_markup=markup)
        

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if user_response == 'Пополнить':
            context.user_data['state'] = Deposit
            await Deposit.pick_bookmaker(update, context)
        elif user_response == 'Вывести':
            context.user_data['state'] = Withdraw
            await Withdraw.pick_bookmaker(update, context)
        else:
            await invalid_reply(update, context)
        
        pass

class NotAgreed():
    
    @staticmethod   
    async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
        text = "🥳 Добро пожаловать, {0}\n🤖 Это бот для Пополнений/Выводов с букмекерских контор\nНажимая на кнопку принять вы соглашаетесь с правилами\nВам исполнилось 18 и более лет\nЗаполнять правильно реквизиты, ID счетов за неверно введенные данные ответственность лежит на вас\n❗️Используйте только свои кошельки для пополнения, администратор может потребовать вывод только на тот кошелек с которого было пополнение\n\n⚠️Не используйте повторный или старый чек "
        
        reply = [
            ["Принять"],
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

        await update.message.reply_text(text.format(update.effective_user.first_name), reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text
        
        if user_response == 'Принять':
            context.user_data['state'] = AgreedState 

            await update.message.reply_text("Вы приняли соглашение!", reply_markup=ReplyKeyboardRemove())
            await AgreedState.welcome(update, context)
        else:
            await invalid_reply(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    if(context.user_data == None):
        return; 
    try: 
        state = context.user_data['state']
    except:        
        state = NotAgreed
        context.user_data['state'] = state
    finally:
        await state.welcome(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (context.user_data == None):
        return
    try: 
        state = context.user_data['state']
        await state.handle_reply(update, context)
    except:
        await invalid_reply(update, context)

def register_handlers(app: Application):     
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))

