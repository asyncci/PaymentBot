from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import admin, json


bookmakers = []

async def getBookmakers():
    return bookmakers

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
                            ['1'],
                            ['Отмена']
                        ]           
                        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                        self.walletId = index

                        await update.message.reply_text('Выберите что изменить:\n1.Название\n\n', reply_markup=markup)
                        self.step += 1
                        return False

                    index += 1
 
                await admin.invalid_reply(update, context)
                return False
            case 3:
                match user_response:
                    case '1':
                        await update.message.reply_text('Введите новое название:')
                        self.item = 1
                        self.step += 1
                        return False
                    case _:
                        await admin.invalid_reply(update, context)
                        return False
            case _:
                wallets = await getBookmakers()
                wallet = wallets[self.walletId]
                match self.item:
                    case 1: 
                        wallet['name'] = user_response
                    case _:
                        exception('Incorrect item changing.')

                await editBookmaker(self.walletId, wallet)
                return True                

               
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        wallet = (await getBookmakers())[self.walletId]
        await update.message.reply_text('Букмекер был изменен!\nНазвание: {}\n'.format(wallet['name']))

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


class AddBookmakerProcess():
    
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
                return True
       
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        await addBookmaker(
            { 
                "name": self.name
            }
        )
        await update.message.reply_text('Букмекер был добавлен!')
    

class Bookmakers():
    @staticmethod
    async def pickAction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Cписок букмекеров'],
            ['Добавить букмекер', 'Удалить букмекер'],
            ['Изменить букмекер'],
            ['Сохранить в базу'],
            ['Отмена']
        ]

        markup = ReplyKeyboardMarkup(reply)
        await update.message.reply_text('Меню настройки кошельков', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        user_response = update.message.text

        if user_response == 'Отмена':
            context.user_data['local_state'] = None
            state = admin.Idle
            context.user_data['state'] = state
            await admin.Idle.settings(update, context)

        elif user_response == 'Cписок букмекеров':
            text = 'Список кошельков: '
            j = 0
            for i in await getBookmakers():
                j += 1
                text += '\n' + str(j) + '.' + i['name']

            await update.message.reply_text(text)
            await Bookmakers.pickAction(update, context)

        elif user_response == 'Добавить букмекер':
            local_state = AddBookmakerProcess()
            context.user_data['local_state'] = local_state
            await local_state.run(update, context, None)
              
        elif user_response == 'Удалить букмекер':
            local_state = DeleteBookmakerProcess()
            context.user_data['local_state'] = local_state
            await local_state.run(update, context, None)

        elif user_response == 'Изменить букмекер':
            local_state = EditBookmakerProcess()
            context.user_data['local_state'] = local_state
            await local_state.run(update, context, None)

        elif user_response == 'Сохранить в базу':
            await saveBookmakersDB()
            await update.message.reply_text('Сохранено в базу')
        else:
            local_state = context.user_data['local_state']
            if local_state == None:
                await admin.invalid_reply(update, context)
                return

            finish = await local_state.run(update, context, user_response) 
            if finish:
                await local_state.finalize(update, context)
                context.user_data['local_state'] = None
                await Bookmakers.pickAction(update, context)
                print(bookmakers)