import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from io import UnsupportedOperation
import json
from logging import captureWarnings, error, exception
from os import execle, getenv, replace
from typing import Any, List, Optional
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from client import DepositProcess, WithdrawProcess
from wallets import Wallets
from bookmakers import Bookmakers

from telegram.ext import ContextTypes

import inspect


load_dotenv()
try:
    ADMIN_ID = int(getenv("ADMIN_ID"))
except:
    error('Admin ID not provided in .env.')
    quit()


async def invalid_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stack = inspect.stack()
    print(f"Function was called from {stack[1].function} in {stack[1].filename} at line {stack[1].lineno}")
    await update.message.reply_text("Нет такого варианта ответа -.")

async def callbackWithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, newWithdraw: WithdrawProcess) -> None:
    if adminInstance.last_state == None:
        state = WithdrawAccept(newWithdraw, adminInstance.state, update, context)
        adminInstance.last_state = state
        if adminInstance.local_state != None:
            adminInstance.next_state = state
            print(vars(adminInstance))
        else:
            adminInstance.state = state
            await adminInstance.state.start(update, context)
    else:
        state = WithdrawAccept(newWithdraw, adminInstance.last_state.previous_state, update, context)
        adminInstance.last_state.next_request_state = state
        adminInstance.last_state = state

async def callbackDeposit(update: Update, context: ContextTypes.DEFAULT_TYPE, newDeposit: DepositProcess) -> None:
    if adminInstance.last_state == None:
        state = DepositAccept(newDeposit, adminInstance.state, update, context)
        adminInstance.last_state = state
        if adminInstance.local_state != None:
            adminInstance.next_state = state
            print(vars(adminInstance))
        else:
            adminInstance.state = state
            await adminInstance.state.start(update, context)
    else:
        state = DepositAccept(newDeposit, adminInstance.last_state.previous_state, update, context)
        adminInstance.last_state.next_request_state = state
        adminInstance.last_state = state


def loadBlockedUsers():
    try:
        with open("blockedUsers.json", "r") as final:
            return json.load(final)
    except FileNotFoundError:
        print("File blockedUsers.json not found.")
        return []
    except:
        print("Errors with json file.")
        return []

blockedUsers = loadBlockedUsers()

async def getBlockedUsers():
    return blockedUsers

async def addBlockedUser(user):
    blockedUsers.append(user)

async def popBlockedUser(id):
    blockedUsers.pop(id)

async def editBlockedUser(id, data):
    blockedUsers[id] = data

async def saveBlockedUsersDB():
    with open("blockedUsers.json", "w") as final:
	    json.dump(blockedUsers, final)

async def blockedUserIDs() -> list[str]:
    bookmakers = await getBlockedUsers()
    list_of_ids = list(map(lambda i: i['id'], bookmakers))
    return list_of_ids

class UnblockProcess():

    def __init__(self) -> None:
        self.step = 1
    
    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:
        match self.step:
            case 1:
                await update.message.reply_text('Введите id пользователя:')
                self.step += 1
                return False
            case 2:
                id = int(user_response)
                blockedUsers = await blockedUserIDs()
                index = 0
                for i in blockedUsers:
                    if i == id:
                        self.index = index
                        self.id = id
                        return True
                    index += 1

                await invalid_reply(update, context)
                return False

    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        try:
            await popBlockedUser(self.index)
            await saveBlockedUsersDB()
            await update.message.reply_text('Пользователь {} был разблокирован.'.format(self.id))
        except:
            await update.message.reply_text('Ошибка при сохранении списка заблокированных пользователей!')
            return

class BlockedUsers():

    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        reply = [
            ['Разблокировать'],
            ['Отмена']
        ]
        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
         
        text = 'Список заблокированных пользователей:\n'

        blockedUsers = await getBlockedUsers()
        index = 1
        for i in blockedUsers:
            show = None
            if i['username'] != None:
                show = '@'+i['username']
            else:
                show = i['name']

            text += str(index)+'.'+str(show)+" id="+str(i['id']) +'\n'

        await update.message.reply_text(text=text, reply_markup=markup)
        pass

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        user_response = update.message.text

        if user_response == 'Отмена':
            adminInstance.local_state = None
            adminInstance.state = Idle
            await adminInstance.finishedState(update, context)
    
        elif user_response == 'Разблокировать':
            local_state = UnblockProcess()
            adminInstance.local_state = local_state 
            await local_state.run(update, context, None)
        else:
            local_state = adminInstance.local_state
            if local_state == None:
                await invalid_reply(update, context)
                return

            finish = await local_state.run(update, context, user_response) 
            if finish:
                await local_state.finalize(update, context)
                adminInstance.local_state = None
                await adminInstance.finishedState(update, context)

class Idle():
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Кошельки', 'Букмекеры'],
            ['Заблокированные пользователи']
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        await update.message.reply_text('Админ панель 👇', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Кошельки':
            adminInstance.state = Wallets
            await Wallets.start(update, context)
        elif user_response == 'Букмекеры':
            adminInstance.state = Bookmakers
            await Bookmakers.start(update, context)
        elif user_response == 'Заблокированные пользователи':
            adminInstance.state = BlockedUsers
            await BlockedUsers.start(update, context)
        else:
            await invalid_reply(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(vars(adminInstance))
    print(update.message.chat)
    if(context.user_data == None):
        return; 
    state = Idle
    adminInstance.state = state
    await state.start(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(vars(adminInstance))
    if (context.user_data == None):
        return
    try: 
        state = adminInstance.state
        await state.handle_reply(update, context)
    except Exception as e:
        print(e)
        await invalid_reply(update, context)


class WithdrawAccept(): 
    def __init__(self, newWithdraw: WithdrawProcess, previous_state: Optional[Any], update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.withdraw = newWithdraw
        self.previous_state = previous_state 
        username = update.message.chat.username
        if username == None:
            self.username = update.message.chat.first_name
        else:
            self.username = "@" + username

        self.chat = update.message.chat
        self.next_request_state = None


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = self.username
        withdraw = self.withdraw
        
        reply = [
            [username],
            ['Принять','Отклонить','Заблокировать']
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        
        text = "ВЫВОД от пользователя: {}\n\nБукмекер: {}\nПополнение по: {}\nId на сайте: {}\nСумма: {}\nКОД: {}".format(username, withdraw.bookmaker, withdraw.wallet['name'], withdraw.id, withdraw.money, withdraw.code)
         
        message = await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)
        self.message_id = message.message_id
        #await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self.next_request_state != None:
            adminInstance.state = self.next_request_state
            await adminInstance.state.start(update, context)
            return

        adminInstance.state = self.previous_state
        adminInstance.last_state = None
        await adminInstance.state.start(update, context)

    async def handle_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Принять':
            await self._accept_message(update, context)
            await context.bot.send_message(reply_to_message_id=self.message_id, text='Принято', chat_id=ADMIN_ID)
            await self.finish(update, context)
        elif user_response == 'Отклонить':
            await self._decline_message(update, context)
            await context.bot.send_message(reply_to_message_id=self.message_id, text='Отклонено', chat_id=ADMIN_ID)
            await self.finish(update, context)
        elif user_response == 'Заблокировать':
            user = {
                'name': self.chat.first_name,
                'username': self.chat.username,
                'id': self.chat.id
            }
            try:
                await addBlockedUser(user)
                await saveBlockedUsersDB()
                await context.bot.send_message(reply_to_message_id=self.message_id, text='Заблокировано', chat_id=ADMIN_ID)
                await self._block_message(update, context)
                await self.finish(update, context)
            except:
                await update.message.reply_text('Ошибка при блокировке, повторите.')
        else:
            await invalid_reply(update, context)

    async def _accept_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Ваша заявка была принята!🎆\nОжидайте Вывод⬇️'
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _decline_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '⚠️ Вывод не выполнен\n⛔️ Вы ввели не верные данные для вывода\n🛟 Если у вас возникли какие то проблемы пишите админстратору: @igrokweb'
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _block_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите @igrokweb'
        await context.bot.send_message(chat_id=self.chat.id, text=text, reply_markup=ReplyKeyboardRemove())


class DepositAccept(): 
    def __init__(self, newDeposit: DepositProcess, previous_state: Optional[Any], update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.deposit = newDeposit
        self.previous_state = previous_state 
        username = update.message.chat.username
        if username == None:
            self.username = update.message.chat.first_name
        else:
            self.username = "@" + username

        self.chat = update.message.chat
        self.next_request_state = None


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = self.username
        deposit = self.deposit
        
        reply = [
            [username],
            ['Принять','Отклонить','Заблокировать']
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        
        names = " ".join(self.deposit.details)
        text = "ПОПОЛНЕНИЕ от пользователя: {}\n\nБукмекер: {}\nПополнение по: {}\nФИО: {}\nId на сайте: {}\nСумма: {}".format(username, deposit.bookmaker, deposit.wallet['name'], names, deposit.id, deposit.money)
        photo = deposit.photo
         
        message = await context.bot.send_photo(chat_id=ADMIN_ID, reply_markup=markup, caption=text, photo=photo[0])
        self.message_id = message.message_id
        #await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self.next_request_state != None:
            adminInstance.state = self.next_request_state
            await adminInstance.state.start(update, context)
            return

        adminInstance.state = self.previous_state
        adminInstance.last_state = None
        await adminInstance.state.start(update, context)

    async def handle_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Принять':
            await self._accept_message(update, context)
            await context.bot.send_message(reply_to_message_id=self.message_id, text='Принято', chat_id=ADMIN_ID)
            await self.finish(update, context)
        elif user_response == 'Отклонить':
            await self._decline_message(update, context)
            await context.bot.send_message(reply_to_message_id=self.message_id, text='Отклонено', chat_id=ADMIN_ID)
            await self.finish(update, context)
        elif user_response == 'Заблокировать':
            user = {
                'name': self.chat.first_name,
                'username': self.chat.username,
                'id': self.chat.id
            }
            try:
                await addBlockedUser(user)
                await saveBlockedUsersDB()
                await context.bot.send_message(reply_to_message_id=self.message_id, text='Заблокировано', chat_id=ADMIN_ID)
                await self._block_message(update, context)
                await self.finish(update, context)
            except:
                await update.message.reply_text('Ошибка при блокировке, повторите.')
        else:
            await invalid_reply(update, context)

    async def _accept_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Ваша заявка была принята!🎆\nОжидайте пополнения '
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _decline_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Депозит не выполнен\n⛔️ Уведомляем за использование поддельного или фальшивого чека, вы подвергаете себя риску поддельных операция ! Пожалуйста соблюдайте правила и будьте внимательны чтобы избежать блокировки'
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _block_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите @igrokweb'
        await context.bot.send_message(chat_id=self.chat.id, text=text, reply_markup=ReplyKeyboardRemove())



class Admin:
    state: Optional[Any] = Idle
    local_state: Optional[Any] = None
    #callback_states: List[DepositAccept | DepositAccept]
    next_state: Optional[Any] = None
    last_state: Optional[Any] = None
    _instance = None  # Class variable to store the instance

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def finishedState(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.next_state != None:
            self.state = self.next_state
            self.next_state = None
        print("goekgoe")
        await self.state.start(update, context)

adminInstance = Admin()
