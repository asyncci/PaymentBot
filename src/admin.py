import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime, timedelta
from functools import update_wrapper
from io import UnsupportedOperation
import json
from logging import captureWarnings, error, exception
from os import execle, getenv, replace, stat
from typing import Any, List, Optional
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram._utils.argumentparsing import parse_lpo_and_dwpp
from client import DepositProcess, WithdrawProcess, getAgreedUsers, loadAgreedUsers
from wallets import Wallets
from bookmakers import Bookmakers

from telegram.ext import CallbackContext, ContextTypes, JobQueue
import re
import inspect


load_dotenv()
try:
    ADMIN_ID = int(getenv("ADMIN_ID"))
except:
    error('Admin ID not provided in .env.')
    quit()

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
    stack = inspect.stack()
    print(f"Function was called from {stack[1].function} in {stack[1].filename} at line {stack[1].lineno}")
    await update.message.reply_text("Нет такого варианта ответа -.")

async def callbackWithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, newWithdraw: WithdrawProcess) -> None:
    id = len(adminInstance.requests)
    state = WithdrawAccept(id, newWithdraw, adminInstance.state, update, context)
    adminInstance.requests.append(state)
    if adminInstance.local_state == None:
        await adminInstance.runRequests(update, context)

async def callbackDeposit(update: Update, context: ContextTypes.DEFAULT_TYPE, newDeposit: DepositProcess) -> None:
    id = len(adminInstance.requests)
    state = DepositAccept(id, newDeposit, adminInstance.state, update, context)
    adminInstance.requests.append(state)
    if adminInstance.local_state == None:
        await adminInstance.runRequests(update, context)

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
class SetTimer(): 
    @staticmethod
    def is_valid_time(time_string):
        """
        Check if the given time string is in HH:MM format and valid.

        Args:
            time_string (str): The time string to check.

        Returns:
            bool: True if the time string is valid, False otherwise.
        """
        pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
        return bool(re.match(pattern, time_string))


    @staticmethod
    def seconds_to_time(target_time):
        """
        Calculate the number of seconds from the current time to a given target time.

        Args:
            target_time (str): The target time in "HH:MM" format.

        Returns:
            int: Number of seconds from the current time to the target time.
        """
        try:
            # Parse the target time
            target = (datetime.strptime(target_time, "%H:%M") - timedelta(hours=3)).time()

            # Get the current time
            print(target)
            now = datetime.now()
            current_time = now.time()

            # Combine the current date with the target time
            target_datetime = datetime.combine(now.date(), target)

            # If the target time is earlier than the current time, assume it's for the next day
            if target <= current_time:
                target_datetime += timedelta(days=1)

            # Calculate the difference in seconds
            time_difference = target_datetime - now
            return int(time_difference.total_seconds())

        except ValueError:
            raise ValueError("Invalid time format. Use 'HH:MM'.")


    def __init__(self) -> None:
        self.step = 1

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:
        reply = [
                ['Отмена']
            ]
        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        
        #get response on previous question and ask actual
        match self.step: 
            case 1:
                await update.message.reply_text('Напишите время рассылки в формате [HH:MM]:', reply_markup=markup)
        
                self.step += 1
                return False
            case 2: 
                #get response for first question
                valid = SetTimer.is_valid_time(user_response)
                if valid == False:
                    await update.message.reply_text('Напишите корректное время в правильном формате!', reply_markup=markup)
                    return False

                self.step += 1
                self.time = user_response
                return True
       
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        time = self.time
        seconds = SetTimer.seconds_to_time(time)
        print(f"Seconds from now to {time}: {seconds}")
        
        if context.job_queue != None:
            current_jobs = context.job_queue.jobs()

            for job in current_jobs:
                job.schedule_removal()
        
        context.job_queue.run_repeating(Newsletter.notifications, timedelta(days=1), seconds)

        await update.message.reply_text('Время было изменено!')

        #save to DB


class Newsletter():
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        local_state = SetTimer()
        adminInstance.local_state = local_state
        await local_state.run(update, context, None)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Отмена':
            adminInstance.local_state = None
            adminInstance.state = Idle
            await adminInstance.finishedState(update, context)
        else: 
            local_state = adminInstance.local_state
            if local_state == None:
                await invalid_reply(update, context)
                return

            finish = await local_state.run(update, context, user_response) 
            if finish:
                await local_state.finalize(update, context)
                adminInstance.local_state = None
                adminInstance.state = Idle
                await adminInstance.finishedState(update, context)

    @staticmethod
    async def notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
        #get chat ids 
        #make newsletter
        users = loadAgreedUsers()
        text = "Бот работает штатном режиме✅\n⏰ Мы всегда на связи : 24/7\n🚀 @GymKassa_KGbot 🚀\n💰 Пополнение | Толуктоо⚡\n💵 Вывод | Чыгаруу ⚡\n/start  /start  /start  /start" 

        for user in users:
            try:
                await context.bot.send_message(chat_id=user, text=text)
            except Exception as e:
                print("Notifications, chat not found.")

class Idle():
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Кошельки', 'Букмекеры'],
            ['Заблокированные пользователи'],
            ['Изменить время рассылки'],
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
        elif user_response == 'Изменить время рассылки':
            adminInstance.state = Newsletter
            await Newsletter.start(update, context)
        else:
            await invalid_reply(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if(context.user_data == None):
        return; 
    state = Idle
    adminInstance.username = update.message.chat.username
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
        await start(update, context)

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    callback_data = json.loads(query.data)
    await adminInstance.acceptRequests(callback_data['id'], callback_data['option'], update, context)
    


class WithdrawAccept(): 
    def __init__(self, id , newWithdraw: WithdrawProcess, previous_state: Optional[Any], update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.withdraw = newWithdraw
        self.previous_state = previous_state 
        username = update.message.chat.username
        if username == None:
            self.username = update.message.chat.first_name
        else:
            self.username = "@" + username

        self.chat = update.message.chat
        self.next_request_state = None
        self.id = id
        self.done = False


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = self.username
        withdraw = self.withdraw
        
        reply = [
             [
                  InlineKeyboardButton('Принять', callback_data=json.dumps({'id': str(self.id), 'option': 'accept'})), 
                  InlineKeyboardButton('Отклонить', callback_data=json.dumps({'id': str(self.id), 'option': 'decline'}))
            ],
            [     InlineKeyboardButton('Заблокировать', callback_data=json.dumps({'id': str(self.id), 'option': 'block'})) 
            ]
        ]

        markup = InlineKeyboardMarkup(reply)
        
        text = "ВЫВОД от пользователя: {}\n\nБукмекер: {}\nId на сайте: `{}`\nВывод по: {}\nНомер: `{}`\nСумма: `{}`\nКОД: `{}`".format(username, withdraw.bookmaker['name'], withdraw.id, withdraw.wallet['name'], withdraw.phone, withdraw.money, withdraw.code)
        
        special_chars = r"_*[]()~>#+-=|{}.!\\"
        text = escape_special_characters(text, special_chars)

        message = await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text, parse_mode='MarkdownV2')
        self.message_id = message.message_id
        #await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.done = True
        #if self.next_request_state != None:
        #    adminInstance.state = self.next_request_state
        #    await adminInstance.state.start(update, context)
        #    return
        #
        #adminInstance.state = self.previous_state
        #adminInstance.last_state = None
        #await adminInstance.state.start(update, context)

    async def button_handler(self, user_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    
        query = update.callback_query
        print("adalkwod: ", query.message)
        message = query.message.text
        
        if user_response == 'accept':
            await self._accept_message(update, context)
            await query.edit_message_text(text=message + "\n\nПринято")
            await self.finish(update, context)
        elif user_response == 'decline':
            await self._decline_message(update, context)
            await query.edit_message_text(text=message + "\n\nОтклонено")
            await self.finish(update, context)
        elif user_response == 'block':
            user = {
                'name': self.chat.first_name,
                'username': self.chat.username,
                'id': self.chat.id
            }
            try:
                await addBlockedUser(user)
                await saveBlockedUsersDB()
                await query.edit_message_text(text=message + "\n\nЗаблокировано")
                await self._block_message(update, context)
                await self.finish(update, context)
            except:
                await update.message.reply_text('Ошибка при блокировке, повторите.')
        else:
            await invalid_reply(update, context)

    async def _accept_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '✅ Вывод выполнен\n💸 Выведено: {} KGS\n🆔 Счет: {}'.format(self.withdraw.money, self.withdraw.id)
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _decline_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '⚠️ Вывод не выполнен\n⛔️ Вы ввели не верные данные для вывода\n🛟 Если у вас возникли какие то вопросы или проблемы пишите админстратору: ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _block_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text, reply_markup=ReplyKeyboardRemove())


class DepositAccept(): 
    def __init__(self, id, newDeposit: DepositProcess, previous_state: Optional[Any], update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.deposit = newDeposit
        self.previous_state = previous_state 
        username = update.message.chat.username
        if username == None:
            self.username = update.message.chat.first_name
        else:
            self.username = "@" + username

        self.chat = update.message.chat
        self.next_request_state = None
        self.id = id
        self.done = False


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = self.username
        deposit = self.deposit
        
        reply = [
             [
                  InlineKeyboardButton('Принять', callback_data=json.dumps({'id': str(self.id), 'option': 'accept'})), 
                  InlineKeyboardButton('Отклонить', callback_data=json.dumps({'id': str(self.id), 'option': 'decline'}))
            ],
            [     InlineKeyboardButton('Заблокировать', callback_data=json.dumps({'id': str(self.id), 'option': 'block'})) 
            ]
        ]

        markup = InlineKeyboardMarkup(reply)
        
        names = " ".join(self.deposit.details)
        text = "ПОПОЛНЕНИЕ от пользователя: {}\n\nБукмекер: {}\nПополнение по: {}\nФИО: {}\nId на сайте: `{}`\nСумма: `{}`".format(username, deposit.bookmaker, deposit.wallet['name'], names, deposit.id, deposit.money)
        photo = deposit.photo
         
        special_chars = r"_*[]()~>#+-=|{}.!\\"
        text = escape_special_characters(text, special_chars)
        
        message = await context.bot.send_photo(chat_id=ADMIN_ID, reply_markup=markup, caption=text, photo=photo[0], parse_mode='MarkdownV2')
        self.message_id = message.message_id
        #await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.done = True    
        #if self.next_request_state != None:
        #    adminInstance.state = self.next_request_state
        #    await adminInstance.state.start(update, context)
        #    return
        #
        #adminInstance.state = self.previous_state
        #adminInstance.last_state = None
        #await adminInstance.state.start(update, context)

    async def button_handler(self, user_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        query = update.callback_query
        message = query.message.caption

        if user_response == 'accept':
            await self._accept_message(update, context)
            await query.edit_message_caption(caption=message + '\n\nПринято')
            await self.finish(update, context)
        elif user_response == 'decline':
            await self._decline_message(update, context)
            await query.edit_message_caption(caption=message + '\n\nОтклонено')
            await self.finish(update, context)
        elif user_response == 'block':
            user = {
                'name': self.chat.first_name,
                'username': self.chat.username,
                'id': self.chat.id
            }
            try:
                await addBlockedUser(user)
                await saveBlockedUsersDB()
                await query.edit_message_caption(caption=message + '\n\nЗаблокировано')
                await self._block_message(update, context)
                await self.finish(update, context)
            except:
                await update.message.reply_text('Ошибка при блокировке, повторите.')
        else:
            await invalid_reply(update, context)

    async def _accept_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '✅ Депозит выполнен\n💸 Ваш счет пополнен: {} KGS\n🆔 Счет: {}'.format(self.deposit.money, self.deposit.id)
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _decline_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Депозит не выполнен\n⛔️ Уведомляем за использование поддельного или фальшивого чека, вы подвергаете себя риску поддельных операция ! Пожалуйста соблюдайте правила и будьте внимательны чтобы избежать блокировки. Если у вас возникли какие то проблемы пишите админстратору: ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _block_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text, reply_markup=ReplyKeyboardRemove())



class Admin:
    state: Optional[Any] = None
    local_state: Optional[Any] = None
    #callback_states: List[DepositAccept | DepositAccept]
    next_state: Optional[Any] = None
    last_state: Optional[Any] = None
    _instance = None  # Class variable to store the instance

    requests: List[DepositAccept|WithdrawAccept] = []
    countReqsDone: int = 0
    
    username: str = ''

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def finishedState(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.runRequests(update, context)
        await self.state.start(update, context)

    async def runRequests(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        for request in self.requests:
            if request.done == False:
                await request.start(update, context)

    async def acceptRequests(self, id, user_response: str, update: Update, context: CallbackContext) -> None:
        id = int(id)
        await self.requests[id].button_handler(user_response, update, context)
        self.countReqsDone += 1
        if self.countReqsDone == len(self.requests):
            self.countReqsDone = 0
            self.requests.clear()

adminInstance = Admin()
