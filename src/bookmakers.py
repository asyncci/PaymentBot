from logging import exception
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import admin, json

def loadBookmakers():
    try:
        with open("bookmakers.json", "r") as final:
            return json.load(final)
    except FileNotFoundError:
        print("File bookmakers.json not found.")
        return []
    except:
        print("Errors with json file.")
        return []

bookmakers = loadBookmakers()

async def getBookmakers():
    return bookmakers

async def getBookmakerByName(name: str) -> dict|None:
    for i in bookmakers:
        if i['name'] == name:
            return i
    return None

async def addBookmaker(wallet):
    bookmakers.append(wallet)

async def deleteBookmaker(id):
    bookmakers.pop(id)

async def editBookmaker(id, data):
    bookmakers[id] = data

async def saveBookmakersDB():
    with open("bookmakers.json", "w") as final:
	    json.dump(bookmakers, final)

async def bookmakerNames() -> list[str]:
    bookmakers = await getBookmakers()
    list_of_names = list(map(lambda i: i['name'], bookmakers))
    return list_of_names

class EditBookmakerProcess():
    
    def __init__(self) -> None:
        self.step = 1

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:

        match self.step:
            case 1: 
                wallet_names = await bookmakerNames()
                reply = [wallet_names]

                reply.append(['Отмена'])
            
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите букмекер, который нужно изменить:', reply_markup=markup)
                
                self.step += 1
                return False
            case 2:
                wallet_names = await bookmakerNames()
                
                index = 0
                for i in wallet_names:

                    if user_response == i:
                        reply = [
                            ['1','2'],
                            ['Отмена']
                        ]           
                        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                        self.walletId = index

                        await update.message.reply_text('Выберите что изменить:\n1.Название\n2.Город\n\n', reply_markup=markup)
                        self.step += 1
                        return False

                    index += 1
 
                await admin.invalid_reply(update, context)
                return False
            case 3:
                reply = [
                        ['Отмена']
                    ]
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)
        
                match user_response:
                    case '1':
                        await update.message.reply_text('Введите новое название:', reply_markup=markup)
                        self.item = 1
                        self.step += 1
                        return False
                    case '2':
                        await update.message.reply_text('Введите новый город:', reply_markup=markup)
                        self.item = 2
                        self.step += 1
                    case _:
                        await admin.invalid_reply(update, context)
                        return False
            case _:
                wallets = await getBookmakers()
                wallet = wallets[self.walletId]
                match self.item:
                    case 1: 
                        wallet['name'] = user_response
                    case 2:
                        wallet['city'] = user_response
                    case _:
                        exception('Incorrect item changing.')

                await editBookmaker(self.walletId, wallet)
                return True                

               
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        wallet = (await getBookmakers())[self.walletId]
        await update.message.reply_text('Букмекер был изменен!\nНазвание: {}\n'.format(wallet['name']))
        await saveBookmakersDB()

class DeleteBookmakerProcess():
    
    def __init__(self) -> None:
        self.step = 0

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:
    
        self.step += 1

        match self.step:
            case 1: 
                wallet_names = await bookmakerNames()
                reply = [wallet_names]

                reply.append(['Отмена'])
            
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите букмекер, который нужно удалить', reply_markup=markup)
                return False
            case _:
                wallet_names = await bookmakerNames()
                
                index = 0
                for i in wallet_names:

                    if user_response == i:
                        await deleteBookmaker(index)
                        return True

                    index += 1
 
                await admin.invalid_reply(update, context)
                return False
               
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        await update.message.reply_text('Букмекер был удален!')
        await saveBookmakersDB()


class AddBookmakerProcess():
    
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
                await update.message.reply_text('Введите имя:', reply_markup=markup)
        
                self.step += 1
                return False
            case 2: 
                #get response for first question
                if user_response in await bookmakerNames():
                    await update.message.reply_text('Такой букмекер уже добавлен.\nВведите другое имя', reply_markup=markup)
                    return False

                self.step += 1
                self.name = user_response

                await update.message.reply_text('Введите город:', reply_markup=markup)
                return False
            case 3: 
                self.city = user_response
                self.step += 1
                return True
       
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        await addBookmaker(
            { 
                "name": self.name,
                "city": self.city,
            }
        )
        await update.message.reply_text('Букмекер был добавлен!')
        await saveBookmakersDB()

class Bookmakers():
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Cписок букмекеров'],
            ['Добавить', 'Удалить', 'Изменить'],
            ['Отмена'],
        ]

        markup = ReplyKeyboardMarkup(reply)
        await update.message.reply_text('Меню настройки букмекеров', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        user_response = update.message.text

        if user_response == 'Отмена':
            admin.adminInstance.local_state = None
            admin.adminInstance.state = admin.Idle
            await admin.adminInstance.finishedState(update, context)

        elif user_response == 'Cписок букмекеров':
            text = 'Список букмекеров: '
            j = 0
            for i in await getBookmakers():
                j += 1
                text += '\n' + str(j) + '.' + i['name'] + " - " + i['city']

            await update.message.reply_text(text)
            await Bookmakers.start(update, context)

        elif user_response == 'Добавить':
            local_state = AddBookmakerProcess()
            admin.adminInstance.local_state = local_state
            await local_state.run(update, context, None)
              
        elif user_response == 'Удалить':
            local_state = DeleteBookmakerProcess()
            admin.adminInstance.local_state = local_state
            await local_state.run(update, context, None)

        elif user_response == 'Изменить':
            local_state = EditBookmakerProcess()
            admin.adminInstance.local_state = local_state
            await local_state.run(update, context, None)

        elif user_response == 'Сохранить в базу':
            await saveBookmakersDB()
            await update.message.reply_text('Сохранено в базу')
        else:
            local_state = admin.adminInstance.local_state
            if local_state == None:
                await admin.invalid_reply(update, context)
                return

            finish = await local_state.run(update, context, user_response) 
            if finish:
                await local_state.finalize(update, context)
                admin.adminInstance.local_state = None
                admin.adminInstance.state = admin.Idle
                await admin.adminInstance.finishedState(update, context)
                print(bookmakers)
