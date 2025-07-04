from functools import update_wrapper
from io import UnsupportedOperation
import json, random
from os import link
import re
from typing import Any, Tuple
from typing_extensions import cast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageOriginHiddenUser, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram._utils.types import ReplyMarkup
from telegram.ext import Application, CommandHandler, MessageHandler  

from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

import cashdesk_api
import linkGenerator
import admin, bookmakers, depositWallets, withdrawWallets
import inspect


def escape_special_characters(text: str, special_characters: str) -> str:
    """
    Escapes special characters in the given text by adding a backslash before each.
    
    :param text: The input string to escape.
    :param special_characters: A string containing all characters to escape.
    :return: The escaped string.
    """
    # Create a regex pattern from the special characters
    pattern = f"([{re.escape(special_characters)}])"
    # Add a backslash before each special character
    escaped_text = re.sub(pattern, r"\\\1", text)
    return escaped_text

async def invalid_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    print(context.user_data['state'])
    stack = inspect.stack()
    print(f"Function was called from {stack[1].function} in {stack[1].filename} at line {stack[1].lineno}")
    await update.message.reply_text("Нет такого варианта ответа.\nПопробуйте ещё раз.")

async def get_bookmakers() -> list[list[str]]:
    bookmakerNames = await bookmakers.bookmakerNames()
    
    batch = []
    
    i = 0
    while i < len(bookmakerNames):
        batch.append(bookmakerNames[i:i+2])
        i += 2

    return batch

async def get_deposit_wallets() -> list[list[str]]:
    walletNames = await depositWallets.walletNames()
    
    batch = []
    
    i = 0
    while i < len(walletNames):
        batch.append(walletNames[i:i+2])
        i += 2

    return batch

async def get_withdraw_wallets() -> list[list[str]]:
    walletNames = await withdrawWallets.walletNames()
    
    batch = []
    
    i = 0
    while i < len(walletNames):
        batch.append(walletNames[i:i+2])
        i += 2

    return batch

class WithdrawProcess():

    def __init__(self) -> None:
        self.step = 1

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:  
        try: 
            details = agreedUsers[str(update.message.chat.id)]['details']
        except:
            details = None

        try:
            bookmakerId = agreedUsers[str(update.message.chat.id)]['bookmakerId']
        except:
            bookmakerId = None
        
        match self.step:
            case 1:
                self.step += 1

                reply = await get_bookmakers()
                reply.append(['Отмена'])

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите букмекер 👇', reply_markup=markup)
                return False
            case 2:
                bookmaker = await bookmakers.getBookmakerByName(user_response)

                if bookmaker == None:
                    await invalid_reply(update, context)
                    return False

                self.bookmaker = bookmaker

                self.step += 1

                reply = await get_withdraw_wallets()
                reply.append(['Отмена'])

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите способ вывода👇', reply_markup=markup)
                return False
            case 3:
                if user_response not in await withdrawWallets.walletNames():
                    await invalid_reply(update, context)
                    return False

                self.step += 1
                
                walletsStack = await withdrawWallets.getWallets()
            
                for i in walletsStack:
                    if i['name'] == user_response:
                        self.wallet = i
                reply: Any

                if details == None:
                    reply = [
                        ['Отмена']
                    ]
                else:
                    reply = [
                        [details],
                        ['Отмена']
                    ]

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                text = "Введите реквизиты для вывода ({}):"
                await update.message.reply_text(text=text.format(self.wallet['name']), reply_markup=markup)
                return False
            case 4:

                self.step += 1
                self.details = user_response

                reply: Any

                if bookmakerId == None:
                    reply = [
                        ['Отмена']
                    ]
                else:
                    reply = [
                        [bookmakerId],
                        ['Отмена']
                    ]

                text = "Введите ID вашего счета {}"
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                await update.message.reply_photo(photo=open('photos/xbet.jpg','rb'), caption=text.format(self.bookmaker['name']), reply_markup=markup) 
                return False
            case 5:
                #check for correct id
                if (user_response == None):
                    await invalid_reply(update, context)
                    return False
                
                newBookmakerId = user_response

                isDigit = newBookmakerId.isdigit()
                if not isDigit:
                    await update.message.reply_text('Введите ID!')
                    return False
                
                #check for user existence at bookmaker database 
                try:
                    user = await cashdesk_api.api.get_user(int(newBookmakerId))

                    if (user['UserId'] == 0):
                        await update.message.reply_text('Пожалуйста убедитесь, что ввели корректный номер.')
                        return False
                except: 
                    await update.message.reply_text('Пожалуйста убедитесь, что ввели корректный номер.')
                    return False

                self.bookmakerId = newBookmakerId

                reply = [
                    ['Отмена']
                ]

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                text = "Введите сумму:"
                await update.message.reply_text(text, reply_markup=markup)

                self.step += 1

                return False
            case 6:
                money = user_response

                try:
                    money = int(money)
                except:
                    await update.message.reply_text('Введите сумму!')
                    return False
 
                reply = [
                    ['Отмена']
                ]
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                
                text='Как получить код:\n\n1. Заходим на сайт букмекера\n2. Вывести со счета\n3. Выбираем наличные\n4. Пишем сумму\n5. Город: {}\n6. Улица: GymKassa\n\nДальше делаем все по инструкции после получения кода введите его здесь.\nВведите код от вывода ({})'.format(self.bookmaker['city'], self.bookmaker['name'])
                await update.message.reply_photo(photo=open('photos/instruction.jpg','rb'),caption=text, reply_markup=markup)

                
                self.step += 1
                self.money = money
                return False
            case _:
                self.code = user_response
                return True

    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> None:
        isSent = await admin.callbackWithdraw(update, context, self)
        if isSent:
            user = agreedUsers[str(update.message.chat.id)]
            await editAgreedUsers(update.message.chat.id, {
                **user,
                "details": self.details,
                "bookmakerId": self.bookmakerId
            })
            await saveAgreedUsersDB()

            await update.message.reply_text('⏳ Заявка на вывод успешно создана, время выплаты от 1 минуты до 3 часов, пожалуйста дождитесь\n\nID аккаунта: {}\nНаписать администратору: '.format(self.bookmakerId) + admin.adminInstance.username)
        else:   
            await update.message.reply_text('Вы уже отправили заявку. Пожалуйста, подождите пока она будет обработана.')

class Withdraw(): 
    @staticmethod
    async def pick_bookmaker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        local_state = WithdrawProcess()
        context.user_data['local_state'] = local_state
        await local_state.run(update, context, None)


    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['state'] = IdleClient
            await IdleClient.welcome(update, context)
        else:
            local_state = context.user_data['local_state']
            if local_state == None:
                await invalid_reply(update, context)
                return

            finish = await local_state.run(update, context, user_response) 

            if finish:
                await local_state.finalize(update, context, user_response)
                context.user_data['local_state'] = None
                context.user_data['state'] = IdleClient
                await IdleClient.welcome(update, context)

class DepositProcess():

    def __init__(self) -> None:
        self.step = 1
    #                                                                                                   return type of tuple: first - isFinished, second - should it skip one step, since data is already stored
    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool: 
        try: 
            clientName = agreedUsers[str(update.message.chat.id)]['clientName']
        except:
            clientName = None

        try:
            bookmakerId = agreedUsers[str(update.message.chat.id)]['bookmakerId']
        except:
            bookmakerId = None
 
        match self.step:
            case 1:
                self.step += 1

                reply = await get_bookmakers()
                reply.append(['Отмена'])

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите букмекер 👇', reply_markup=markup)
                return False
            case 2:
                if user_response not in await bookmakers.bookmakerNames() :
                    await invalid_reply(update, context)
                    return False

                self.step += 1
                self.bookmaker = user_response

#                reply = await get_deposit_wallets()
                reply = [['Отмена']]

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

#                 await update.message.reply_text('Выберите способ пополнения👇', reply_markup=markup)
#                 return False
#             case 3:
#                 if user_response not in await depositWallets.walletNames():
#                     await invalid_reply(update, context)
#                     return False
# 
#                 self.step += 1
#                 
#                 walletsStack = await depositWallets.getWallets()
# 
#                 for i in walletsStack:
#                     if i['name'] == user_response:
#                         self.wallet = i
# 
                reply: Any
                
                if clientName == None:
                    reply = [
                        ['Отмена']
                    ]
                else:
                    reply = [
                        [" ".join(clientName)],
                        ['Отмена']
                    ]

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                text = "⚠️ Пожалуйста введите ваше имя и фамилию, чтобы идентифицировать ваше пополнение, при неверном имени пополнение будет отказано:"
                await update.message.reply_photo(photo=open('photos/mbank.jpg','rb'), caption=text, reply_markup=markup)
                return False 

            case 3:
                #check for correct name
                if user_response == None:
                    await update.message.reply_text('❗️Будьте внимательны повторите ввод Имени и Фамилии отправителя:')
                    return False

                newClientName = user_response.split(' ')
                if len(newClientName) < 2:
                    try:
                        if len(newClientName[0]) < 2 and len(newClientName[1]) < 2:
                            await update.message.reply_text('❗️Будьте внимательны повторите ввод Имени и Фамилии отправителя:')
                            return False
                    except:
                        await update.message.reply_text('❗️Будьте внимательны повторите ввод Имени и Фамилии отправителя:')
                        return False
                self.clientName = newClientName

                self.step += 1
 
                reply: Any
                
                if bookmakerId == None:
                    reply = [
                        ['Отмена']
                    ]
                else:
                    reply = [
                        [bookmakerId],
                        ['Отмена']
                    ]

                text = "Введите ID вашего счета {}"
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                await update.message.reply_photo(photo=open('photos/xbet.jpg','rb'), caption=text.format(self.bookmaker), reply_markup=markup) 
                return False

            case 4:
                #check for correct id
                if (user_response == None):
                    await invalid_reply(update, context)
                    return False

                newBookmakerId = user_response
 
                isDigit = newBookmakerId.isdigit()
                if isDigit == False:
                    await update.message.reply_text('Введите ID!')
                    return False
                #check for user existence at bookmaker database 
                try:
                    user = await cashdesk_api.api.get_user(int(newBookmakerId))

                    if (user['UserId'] == 0):
                        await update.message.reply_text('Пожалуйста убедитесь, что ввели корректный номер.')
                        return False
                except: 
                    await update.message.reply_text('Пожалуйста убедитесь, что ввели корректный номер.')
                    return False

                self.bookmakerId = newBookmakerId
                self.step += 1

                reply = [
                    ['50', '100'],
                    ['200', '500', '2000'],
                    ['Отмена']
                ]

                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                text = "Введите сумму или выберите из списка пополнения KGS\nМинимум: 50\nМаксимум: 50000"
                await update.message.reply_text(text, reply_markup=markup)

                return False
            case 5:
                money = user_response

                try:
                    money = int(money)
                except:
                    await update.message.reply_text('Введите сумму!')
                    return False
                #TODO
                if money < 50 or money > 50000:
                    await update.message.reply_text('Введите разрешимую сумму!')
                    return False

                warning_text = '⚠️ Пополнение от 3х лиц запрещено, используйте только свой кошелек\n❗️Терминал, единицы пополнение строго запрещено, вы потеряете деньги если пополните с терминала'
                await update.message.reply_text(warning_text)

                reciever_details = '✅Сумма к оплате: `{}`' 
                hosts = linkGenerator.hosts
                #links to banks
                buttons = [
                    [
                        InlineKeyboardButton(text=hosts['o_dengi']['name'], url=linkGenerator.generate(hosts['o_dengi']['host'], admin.adminInstance.payment_qr_link)), 
                        InlineKeyboardButton(text=hosts['kompanion']['name'], url=linkGenerator.generate(hosts['kompanion']['host'], admin.adminInstance.payment_qr_link)),
                     ],
                    [
                        InlineKeyboardButton(text=hosts['bakai24']['name'], url=linkGenerator.generate(hosts['bakai24']['host'], admin.adminInstance.payment_qr_link)), 
                        InlineKeyboardButton(text=hosts['megapay']['name'], url=linkGenerator.generate(hosts['megapay']['host'], admin.adminInstance.payment_qr_link)),
                     ],
                    [
                        InlineKeyboardButton(text=hosts['mbank']['name'], url=linkGenerator.generate(hosts['mbank']['host'], admin.adminInstance.payment_qr_link)), 
                        InlineKeyboardButton(text=hosts['balance_kg']['name'], url=linkGenerator.generate(hosts['balance_kg']['host'], admin.adminInstance.payment_qr_link)) 
                     ]
                ]

                markup = InlineKeyboardMarkup(buttons)

                await update.message.reply_text(reciever_details.format(money), parse_mode='MarkdownV2', reply_markup=markup)
 

                reply = [
                    ['Отмена']
                ]
                back_markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
                await update.message.reply_text('ℹ️  Оплатите и отправьте скриншот чека в течении 5 минут, чек должен быть в формате картинки 📎', reply_markup=back_markup) 
                
                self.step += 1
                self.money = money

                return False
            case _:
                photo = update.message.photo
                if len(photo) == 0:
                    await update.message.reply_text('Требуется скриншот!')
                    return False

                self.photo = photo
                return True

    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> None:
        isSent = await admin.callbackDeposit(update, context, self)
        if isSent:
            user = agreedUsers[str(update.message.chat.id)]
            await editAgreedUsers(update.message.chat.id, {
                **user,
                "clientName": self.clientName,
                "bookmakerId": self.bookmakerId,
            }) 
            await saveAgreedUsersDB()

            await update.message.reply_text('⏳ Идет проверка...\n\nЕсли проверка занимает больше 10 минут пожалуйста напишите: ' + admin.adminInstance.username)
        else:
            await update.message.reply_text('Вы уже отправили заявку. Пожалуйста подождите пока она будет обработана')

class Deposit(): 
    @staticmethod
    async def pick_bookmaker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        local_state = DepositProcess()
        context.user_data['local_state'] = local_state
        await local_state.run(update, context, None)


    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['state'] = IdleClient
            await IdleClient.welcome(update, context)
        else:
            local_state = context.user_data['local_state']
            if local_state == None:
                await invalid_reply(update, context)
                return

            finish: bool

            finish = await local_state.run(update, context, user_response)          

            if finish:
                await local_state.finalize(update, context, user_response)
                context.user_data['local_state'] = None
                context.user_data['state'] = IdleClient
                await IdleClient.welcome(update, context)

class IdleClient():
    @staticmethod   
    async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = "Добро пожаловать в GYM Kassa⚽️\n\n⚡️ Моментальные пополнения\n"
    
        reply = [
            ['Пополнить', 'Вывести'],
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

        await update.message.reply_text(text, reply_markup=markup)
        

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_response = update.message.text

        if admin.adminInstance.technical_jobs == True:
            await update.message.reply_text('Ведутся технические работы.\nПопробуйте позже.')
            return 
        
        if user_response == 'Пополнить':
            if update.message.chat.id in admin.adminInstance.requests:
                await update.message.reply_text('Предыдущая заявка отправлена. Пожалуйста, подождите пока предыдущая заявка будет обработана.')
                return

            context.user_data['state'] = Deposit
            await Deposit.pick_bookmaker(update, context)
            return
        elif user_response == 'Вывести':
            if update.message.chat.id in admin.adminInstance.requests:
                await update.message.reply_text('Предыдущая заявка отправлена. Пожалуйста, подождите пока предыдущая заявка будет обработана.')
                return

            context.user_data['state'] = Withdraw
            await Withdraw.pick_bookmaker(update, context)
            return
        else:
            await invalid_reply(update, context)
        
        pass



def loadAgreedUsers():
    try:
        with open("agreedUsers.json", "r") as final:
            return json.load(final)
    except FileNotFoundError:
        print("File agreedUsers.json not found.")
        return {}
    except:
        print("Errors with agreedUsers.json file.")
        return {}

agreedUsers = loadAgreedUsers()

async def getAgreedUsers():
    return agreedUsers

async def addAgreedUsers(id):
    agreedUsers[str(id)] = {}

async def deleteAgreedUsers(id):
    del agreedUsers[str(id)]

async def editAgreedUsers(id, data):
    agreedUsers[str(id)] = data

async def saveAgreedUsersDB():
    with open("agreedUsers.json", "w") as final:
	    json.dump(agreedUsers, final)

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
            try:
                await addAgreedUsers(update.message.chat.id)
                await saveAgreedUsersDB()
                await update.message.reply_text("Вы приняли соглашение!", reply_markup=ReplyKeyboardRemove())
                context.user_data['state'] = IdleClient 
                await IdleClient.welcome(update, context)
            except:
                await update.message.reply_text('Ошибка.\nПопробуйте ещё раз.')
        else:
            await invalid_reply(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    if(context.user_data == None):
        return;
    
    if admin.adminInstance.technical_jobs == True:
        await update.message.reply_text('Ведутся технические работы.\nПопробуйте позже.')
        return

    user = update.message.chat.id
    if str(user) not in agreedUsers:
        state = NotAgreed
    else:
        state = IdleClient

    context.user_data['state'] = state
    await state.welcome(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (context.user_data == None):
        return
    try: 
        state = context.user_data['state']

        await state.handle_reply(update, context)
    except Exception as e:
        print(e)
        await start(update, context)


#remember
#id
#first name, last name
#details
