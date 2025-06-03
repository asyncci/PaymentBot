import pickle
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime, timedelta
from functools import update_wrapper
from io import UnsupportedOperation
import json
from logging import captureWarnings, error, exception
from os import execle, getenv, replace, stat
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram._utils.argumentparsing import parse_lpo_and_dwpp
import cashdesk_api
from client import DepositProcess, WithdrawProcess, admin, getAgreedUsers, loadAgreedUsers
from main import TECHNICIAN_ID, technical_jobs
from bookmakers import Bookmakers

import depositWallets, withdrawWallets

from telegram.ext import CallbackContext, ContextTypes, JobQueue
import re
import inspect
import pytz
import os

load_dotenv()
try:
    ADMIN_ID = int(getenv("ADMIN_ID"))
except:
    error('Admin ID not provided in .env.')
    quit()

def saveRequests(requests):
    data_bytes = pickle.dumps(requests)
    with open("requests.pkl", "wb") as f:
        f.write(data_bytes)

def loadRequests():
    try:
        with open("requests.pkl", "rb") as f:
            loaded_requests = pickle.load(f)
            return loaded_requests
    except:
        return {}



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

async def callbackWithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, newWithdraw: WithdrawProcess) -> bool:
    chat_id = update.message.chat.id

    if chat_id in adminInstance.requests:
        await update.message.reply_text("У вас висит заявка, пожалуйста подождите пока она будет обработана.")
        return False
    
    state = WithdrawAccept(newWithdraw, adminInstance.state, update, context)
    adminInstance.requests[chat_id] = state
    if adminInstance.local_state == None:
        await adminInstance.runRequests(update, context)
    return True

async def callbackDeposit(update: Update, context: ContextTypes.DEFAULT_TYPE, newDeposit: DepositProcess) -> bool:
    chat_id = update.message.chat.id
    
    if chat_id in adminInstance.requests:
        await update.message.reply_text("У вас висит заявка, пожалуйста подождите пока она будет обработана.")
        return False

    state = DepositAccept(newDeposit, adminInstance.state, update, context)
    adminInstance.requests[chat_id] = state
    if adminInstance.local_state == None:
        await adminInstance.runRequests(update, context)
    return True 

def loadBlockedUsers():
    try:
        with open("blockedUsers.json", "r") as final:
            return json.load(final)
    except FileNotFoundError:
        print("File blockedUsers.json not found.")
        return []
    except:
        print("Errors with blockedUsers.json file.")
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


def loadAdminSettings() -> Dict[str, Any]:
    try:
        with open("adminSettings.json", "r") as final:
            return json.load(final)
    except FileNotFoundError:
        with open("adminSettings.json", "w") as final:
            json.dump({}, final, indent=4)
        return {}

async def saveAdminSettings():
    with open("adminSettings.json", "w") as final:
	    json.dump(adminSettings, final)

settings = loadAdminSettings()

if settings is None:
    raise ValueError("Expected a value")

adminSettings: Dict[str, Any] = settings

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
            
            reply = [
                ['Пополнить', 'Вывести'],
            ]

            markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
            await context.bot.send_message(self.id, text="Вы были разблокированы! Поздравляем, теперь вы можете снова пользоваться ботом.🎉", reply_markup=markup)
      
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
        await update.message.reply_text(text=text, reply_markup=markup)

        text = ''
        blockedUsers = await getBlockedUsers()
        index = 0
        for user in blockedUsers:
            show = None
            if user['username'] != None:
                show = '@'+user['username']
            else:
                show = user['name']
            
            index += 1
            text += str(index)+'.'+str(show)+" id="+str(user['id']) +'\n'
            
            if len(text) > 2096:
                await update.message.reply_text(text=text, reply_markup=markup)
                text = ''
        
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
    def seconds_to_time(target_time, local_timezone="Asia/Bishkek", server_timezone="Etc/UTC"):
        """
        Calculate the number of seconds from the current time (in UTC) to a given target time in the user's timezone.

        Args:
            target_time (str): The target time in "HH:MM" format (in the local timezone).
            local_timezone (str): The timezone where the target time is set (default is "Asia/Bishkek").
            server_timezone (str): The server's timezone (default is "Etc/UTC").

        Returns:
            int: Number of seconds from the current time (in UTC) to the target time.
        """
        try:
            # Parse the target time
            target = datetime.strptime(target_time, "%H:%M").time()

            # Get the current time in the server's timezone (UTC)
            server_tz = pytz.timezone(server_timezone)
            now_utc = datetime.now(server_tz)

            # Get the local timezone object
            local_tz = pytz.timezone(local_timezone)

            # Combine the target time with today's date in the local timezone
            local_datetime = datetime.combine(now_utc.date(), target)
            local_datetime = local_tz.localize(local_datetime)  # Localize to the local timezone

            # Convert the localized time to UTC
            target_utc = local_datetime.astimezone(server_tz)

            # If the target time in UTC is earlier than the current UTC time, move it to the next day
            if target_utc <= now_utc:
                target_utc += timedelta(days=1)

            # Calculate the difference in seconds
            time_difference = target_utc - now_utc
            return int(time_difference.total_seconds())

        except ValueError:
            raise ValueError("Invalid time format. Use 'HH:MM'.")
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {local_timezone} or {server_timezone}")


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
        if not adminInstance.technical_jobs:
            users = loadAgreedUsers()
            text = "⚜️Пополнение – АКТИВНО ✅\n⚜️ Вывод средств – АКТИВЕН ✅\n⚡️ Наш сервис работает 24/7! ⚡️ Быстро, 🔐 надежно и 🪙 удобно.\n\n❤️Получите бонус уже сейчас!\n🔓 Промокод: GYMKASSA\n❤️ (До 35 000 сом на ваш счет!)\n\n😀 Почему выбирают нас?\n😀 Моментальные операции – без ожиданий.\n🛡Надежность – ваши средства под защитой.\n📞 Поддержка 24/7 – всегда на связи.\n👌 Удобство – простой и понятный сервис.\n\n💡Как получить бонус?\n⚡️ Зарегистрируйтесь на платформе.\n⚡️ Введите промокод GYMKASSA\n⚡️ Заберите свой бонус и начните зарабатывать!\n\n✉️ Есть вопросы? Пишите нам: @igrokweb\n❤️Бот: @GymKassa_KGbot\n💛 С нами легко,выгодно и безопасно! Присоединяйтесь!" 
            for user, _ in users.items():
                try:
                    await context.bot.send_message(chat_id=user, text=text)
                except Exception as e:
                    print("Notifications, chat not found.")

class Idle():
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Кошельки пополнения'],
            ['Кошельки вывода'],
            ['Букмекеры'],
            ['Заблокированные пользователи'],
            ['Изменить время рассылки'],
            ['Вкл/Выкл Технические работы']
        ]

        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        await update.message.reply_text('Админ панель 👇', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        user_response = update.message.text
        
        if user_response == 'Кошельки пополнения':
            adminInstance.state = depositWallets.Wallets
            await depositWallets.Wallets.start(update, context)
        elif user_response == 'Кошельки вывода':
            adminInstance.state = withdrawWallets.Wallets
            await withdrawWallets.Wallets.start(update, context)
        elif user_response == 'Букмекеры':
            adminInstance.state = Bookmakers
            await Bookmakers.start(update, context)
        elif user_response == 'Заблокированные пользователи':
            adminInstance.state = BlockedUsers
            await BlockedUsers.start(update, context)
        elif user_response == 'Изменить время рассылки':
            adminInstance.state = Newsletter
            await Newsletter.start(update, context)
        elif user_response == 'Вкл/Выкл Технические работы':
            await adminInstance.technicalJobOnOff()
            await technicianInstance.afterTechnicalButtonFromAdmin(update, context)
            if adminInstance.technical_jobs == True:
                await update.message.reply_text('Технические работы были ВКЛЮЧЕНЫ.')
            else:
                await update.message.reply_text('Технические работы были ВЫКЛЮЧЕНЫ.') 
        else:
            await invalid_reply(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if(context.user_data == None):
        return; 

    if admin.adminInstance.technical_jobs == True:
        await update.message.reply_text('Технические работы ВКЛЮЧЕНЫ')

    state = Idle
    adminInstance.username = update.message.chat.username
    adminInstance.state = state
    await state.start(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        self.shown_to_admin = False


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = self.username
        withdraw = self.withdraw
        
        reply = [
             [
                  InlineKeyboardButton('Принять', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'accept'})), 
                  InlineKeyboardButton('Отклонить', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'decline'}))
            ],
            [     InlineKeyboardButton('Заблокировать', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'block'})) 
            ]
        ]

        markup = InlineKeyboardMarkup(reply)
        
        text = "ВЫВОД от пользователя: {}\n\nБукмекер: {}\nId на сайте: `{}`\nВывод по: {}\nНомер: `{}`\nСумма клиента: `{}`\nКОД: `{}`".format(username, withdraw.bookmaker['name'], withdraw.bookmakerId, withdraw.wallet['name'], withdraw.details, withdraw.money, withdraw.code)
        
        special_chars = r"_*[]()~>#+-=|{}.!\\"
        text = escape_special_characters(text, special_chars)

        message = await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text, parse_mode='MarkdownV2')
        self.message_id = message.message_id
        self.shown_to_admin = True   
        #await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del adminInstance.requests[self.chat.id]
        #if self.next_request_state != None:
        #    adminInstance.state = self.next_request_state
        #    await adminInstance.state.start(update, context)
        #    return
        #
        #adminInstance.state = self.previous_state
        #adminInstance.last_state = None
        #await adminInstance.state.start(update, context)

    async def _accept(self, query, message) -> bool:
        try:
            payout = await cashdesk_api.api.payout(int(self.withdraw.bookmakerId), code=self.withdraw.code)
            
            if (payout['Success'] == False):
                await query.edit_message_text(text=message + '\n\nВывод невозможен\n\n{}'.format(self.chat.id, payout['Message']))
                return False
            else:
                await query.edit_message_text(text=message + '\n\nПроизведен ✅\nСумма на стороне букмекера: {}'.format(self.chat.id, payout))
                return True
        except: 
            await query.edit_message_text(text=message + '\n\nВывод невозможен.\nОшибка')

        return False

    async def button_handler(self, user_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    
        query = update.callback_query
        message = query.message.text
        done = False

        if user_response == 'accept':
            reply = [
                [ 
                     InlineKeyboardButton('Да, Принять', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'acceptSure'})),
                     InlineKeyboardButton('Назад', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'back'}))
                ]
            ]

            markup = InlineKeyboardMarkup(reply)
            await query.edit_message_reply_markup(reply_markup=markup)
       
        elif user_response == 'acceptSure':
            try:
                accepted = await self._accept(query, message)
                if (accepted):
                    reply = [
                        [ 
                             InlineKeyboardButton('Оповестить о принятии заявки', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'notifyAcceptance'})),
                        ]
                    ]

                    markup = InlineKeyboardMarkup(reply)
                    await query.edit_message_reply_markup(reply_markup=markup)
                else:
                    await self.__default_inline(query)
            except Exception as e:
                print ("Withdraw: ", e)
                await update.message.reply_text("Ошибка при выполнении запроса Withdraw:\n{}".format(e))

        elif user_response == 'notifyAcceptance': 
            await self._accept_message(update, context)
            await query.edit_message_text(text=message + "\n\nОповещен")
            await self.finish(update, context)
            done = True

        elif user_response == 'decline':
            reply = [
                [ 
                     InlineKeyboardButton('Да, Отклонить', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'declineSure'})),
                     InlineKeyboardButton('Назад', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'back'}))
                ]
            ]

            markup = InlineKeyboardMarkup(reply)
            await query.edit_message_reply_markup(reply_markup=markup)
        elif user_response == 'declineSure':
            await self._decline_message(update, context)
            await query.edit_message_text(text=message + "\n\nОтклонено")
            await self.finish(update, context)
            done = True
        elif user_response == 'block':
            reply = [
                [ 
                     InlineKeyboardButton('Да, Заблокировать', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'blockSure'})),
                     InlineKeyboardButton('Назад', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'back'}))
                ]
            ]

            markup = InlineKeyboardMarkup(reply)
            await query.edit_message_reply_markup(reply_markup=markup)
        elif user_response == 'blockSure':
            user = {
                'name': self.chat.first_name,
                'username': self.chat.username,
                'id': self.chat.id
            }
            try:
                await addBlockedUser(user)
                await saveBlockedUsersDB()
                await query.edit_message_text(text=message + '\n\nЗаблокировано')
                await self._block_message(update, context)
                await self.finish(update, context)
                done = True
            except:
                await update.message.reply_text('Ошибка при блокировке, повторите.')
        elif user_response == "back":
            await self.__default_inline(query)
        else:
            await invalid_reply(update, context)

        if done and adminInstance.technical_jobs:
            await technicianInstance.editMessage(context, self.chat.id, self.__class__.__name__)

        if done and adminInstance.technical_jobs:
            await technicianInstance.editMessage(context, self.chat.id, self.chat.__class__.__name__)
        return 

    async def _accept_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '✅ Вывод выполнен\n💸 Выведено: {} KGS\n🆔 Счет: {}'.format(self.withdraw.money, self.withdraw.bookmakerId)
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _decline_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '⚠️ Вывод не выполнен\n⛔️ Вы ввели не верные данные для вывода\n🛟 Если у вас возникли какие то вопросы или проблемы пишите админстратору: ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _block_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text, reply_markup=ReplyKeyboardRemove())
    
    async def __default_inline(self, query):
        reply = [
            [
                 InlineKeyboardButton('Принять', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'accept'})), 
                 InlineKeyboardButton('Отклонить', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'decline'}))
            ],
            [ 
                 InlineKeyboardButton('Заблокировать', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'block'})),
            ]
        ]

        markup = InlineKeyboardMarkup(reply)
        await query.edit_message_reply_markup(reply_markup=markup)

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
        self.shown_to_admin = False


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = self.username
        deposit = self.deposit
        
        reply = [
             [
                  InlineKeyboardButton('Принять', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'accept'})), 
                  InlineKeyboardButton('Отклонить', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'decline'}))
            ],
            [     InlineKeyboardButton('Заблокировать', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'block'})) 
            ]
        ]

        markup = InlineKeyboardMarkup(reply)
        
        names = " ".join(self.deposit.clientName)
        text = "{}\n\nПОПОЛНЕНИЕ от пользователя: {}\n\nБукмекер: {}\nПополнение по: {}\nФИО: {}\nId на сайте: `{}`\nСумма от клиента: `{}`".format(self.chat.id,username, deposit.bookmaker, deposit.wallet['name'], names, deposit.bookmakerId, deposit.money)
        photo = deposit.photo
         
        special_chars = r"_*[]()~>#+-=|{}.!\\"
        text = escape_special_characters(text, special_chars)
        
        message = await context.bot.send_photo(chat_id=ADMIN_ID, reply_markup=markup, caption=text, photo=photo[0], parse_mode='MarkdownV2')
        self.message_id = message.message_id
        self.shown_to_admin = True   
        #await context.bot.send_message(chat_id=ADMIN_ID, reply_markup=markup, text=text)

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del adminInstance.requests[self.chat.id]
        #if self.next_request_state != None:
        #    adminInstance.state = self.next_request_state
        #    await adminInstance.state.start(update, context)
        #    return
        #
        #adminInstance.state = self.previous_state
        #adminInstance.last_state = None
        #await adminInstance.state.start(update, context)

    async def _accept(self, query, message) -> bool:
        try:
            deposit = await cashdesk_api.api.deposit(int(self.deposit.bookmakerId), self.deposit.money)
            
            if (deposit['Success'] == False):
                await query.edit_message_caption(caption=message + '\n\nПополнение невозможно\n\n{}'.format(self.chat.id,deposit['Message']))
                return False
            else:
                await  query.edit_message_caption(caption=message + '\n\nПроизведено ✅\nСумма на стороне букмекера: {}'.format(self.chat.id, deposit))
                return True
                
        except: 
            await query.edit_message_caption(caption=message + '\n\nПополнение невозможно.\nОшибка')

        return False


    async def button_handler(self, user_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        query = update.callback_query
        message = query.message.caption
        done = False

        if user_response == 'accept':
            reply = [
                [
                     InlineKeyboardButton('Да, Принять', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'acceptSure'})), 
                     InlineKeyboardButton('Назад', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'back'}))
                ],
            ]

            markup = InlineKeyboardMarkup(reply)
            await query.edit_message_reply_markup(reply_markup=markup)
        elif user_response == 'acceptSure':
            try:
                accepted = await self._accept(query, message) 
                if (accepted):
                    reply = [
                        [ 
                             InlineKeyboardButton('Оповестить о принятии заявки', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'notifyAcceptance'})),
                        ]
                    ]

                    markup = InlineKeyboardMarkup(reply)
                    await query.edit_message_reply_markup(reply_markup=markup)
                else:
                    await self.__default_inline(query)
            except Exception as e:
                print("Deposit: ", e)
                await update.message.reply_text("Ошибка при выполнении запроса Deposit:\n{}".format(e))

        elif user_response == 'notifyAcceptance':
            await self._accept_message(update, context)
            await query.edit_message_caption(caption=message + '\n\nОповещен')
            await self.finish(update, context)
            done = True
        elif user_response == 'decline':
            reply = [
                [
                     InlineKeyboardButton('Да, Отклонить', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'declineSure'})),
                     InlineKeyboardButton('Назад', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'back'}))
                ],
            ]

            markup = InlineKeyboardMarkup(reply)
            await query.edit_message_reply_markup(reply_markup=markup)
        elif user_response == 'declineSure':
            await self._decline_message(update, context)
            await self.finish(update, context)
            done = True
        elif user_response == 'block':
            reply = [
                [ 
                     InlineKeyboardButton('Да, Заблокировать', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'blockSure'})),
                     InlineKeyboardButton('Назад', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'back'}))
                ]
            ]

            markup = InlineKeyboardMarkup(reply)
            await query.edit_message_reply_markup(reply_markup=markup)
        elif user_response == 'blockSure':
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
                done = True
            except:
                await update.message.reply_text('Ошибка при блокировке, повторите.')
        elif user_response == "back":
            await self.__default_inline(query)
        else:
            await invalid_reply(update, context)

        if done and adminInstance.technical_jobs:
            await technicianInstance.editMessage(context, self.chat.id, self.__class__.__name__)

    async def _accept_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = '✅ Депозит выполнен\n💸 Ваш счет пополнен: {} KGS\n🆔 Счет: {}'.format(self.deposit.money, self.deposit.bookmakerId)
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _decline_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Депозит не выполнен\n⛔️ Уведомляем за использование поддельного или фальшивого чека, вы подвергаете себя риску поддельных операция ! Пожалуйста соблюдайте правила и будьте внимательны чтобы избежать блокировки. Если у вас возникли какие то проблемы пишите админстратору: ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text)

    async def _block_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите ' + '@' + adminInstance.username
        await context.bot.send_message(chat_id=self.chat.id, text=text, reply_markup=ReplyKeyboardRemove())

    async def __default_inline(self, query):
        reply = [
            [
                 InlineKeyboardButton('Принять', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'accept'})), 
                 InlineKeyboardButton('Отклонить', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'decline'}))
            ],
            [ 
                 InlineKeyboardButton('Заблокировать', callback_data=json.dumps({'id': str(self.chat.id), 'option': 'block'})),
            ]
        ]

        markup = InlineKeyboardMarkup(reply)
        await query.edit_message_reply_markup(reply_markup=markup)


class Admin:
    state: Optional[Any] = None
    local_state: Optional[Any] = None
    #callback_states: List[DepositAccept | DepositAccept]
    next_state: Optional[Any] = None
    last_state: Optional[Any] = None
    technical_jobs: bool = False
    _instance = None  # Class variable to store the instance

    requests: Dict[int, DepositAccept|WithdrawAccept] = {}
    countReqsDone: int = 0
    
    username: str = ''

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        try: 
            technical_jobs = adminSettings['technical_jobs']
        except:
            technical_jobs = "false"

        self.requests = loadRequests()

        if technical_jobs == "true":
            self.technical_jobs = True
        else:
            self.technical_jobs = False

    async def technicalJobOnOff(self):
        self.technical_jobs = not self.technical_jobs

        if self.technical_jobs:
            adminSettings['technical_jobs'] = "true" 
        else:
            adminSettings['technical_jobs'] = "false"
       
        await saveAdminSettings()

    async def finishedState(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.runRequests(update, context)
        await self.state.start(update, context)

    async def runRequests(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        print("requests: ", self.requests)
        for key, value in self.requests.items():
            if value.shown_to_admin == False:
                await value.start(update, context)
                 
                if self.technical_jobs == True:
                    message = await context.bot.send_message(chat_id=TECHNICIAN_ID, text="Chat id {}: {} request".format(value.chat.id, value.__class__.__name__))
                    technicianInstance.messages[key] = message                                                            
                

    async def acceptRequests(self, id, user_response: str, update: Update, context: CallbackContext) -> None:
        id = int(id)
        await self.requests[id].button_handler(user_response, update, context)

adminInstance = Admin()


class Technician:
    messages: Dict[int, Message] = {}

    _instance = None  # Class variable to store the instance
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def afterTechnicalButtonFromAdmin(self, update, context: ContextTypes.DEFAULT_TYPE):
        if admin.adminInstance.technical_jobs == True:
            await context.bot.send_message(chat_id=TECHNICIAN_ID, text="Технические работы были включены со стороны Админа")
            
            await context.bot.send_message(chat_id=TECHNICIAN_ID, text="Ongoing requests:")
            for key, value in admin.adminInstance.requests.items(): 
                requestName = value.__class__.__name__
                message = await context.bot.send_message(chat_id=TECHNICIAN_ID, text="Chat id {}: {} request".format(key, requestName))
                admin.technicianInstance.messages[key] = message

        else:
            await context.bot.send_message(chat_id=TECHNICIAN_ID, text="Технические работы были отключены со стороны Админа")

    async def afterTechnicalButton(self, update, context: ContextTypes.DEFAULT_TYPE):
        if admin.adminInstance.technical_jobs == True:
            await update.message.reply_text('Технические работы включены')
            #notify Admin about techincal jobs
            await context.bot.send_message(chat_id=ADMIN_ID, text="Технические работы были ВКЛЮЧЕНЫ со стороны специалиста")
            

            await update.message.reply_text('Ongoing requests:')
            for key, value in admin.adminInstance.requests.items(): 
                requestName = value.__class__.__name__
                message = await update.message.reply_text("Chat id {}: {} request".format(key, requestName))
                admin.technicianInstance.messages[key] = message

        else:
            await update.message.reply_text('Технические работы отключены')
            await context.bot.send_message(chat_id=ADMIN_ID, text="Технические работы были ОТКЛЮЧЕНЫ со стороны специалиста")

    async def editMessage(self, context: CallbackContext, chatId: int, nameClass: str):
        await context.bot.edit_message_text(chat_id=TECHNICIAN_ID, message_id=technicianInstance.messages[chatId].id , text="Chat id {}: {} request DONE".format(chatId, nameClass))

technicianInstance = Technician()


