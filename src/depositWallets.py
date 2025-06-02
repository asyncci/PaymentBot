from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import admin, json

def loadWallets():
    try:
        with open("wallets.json", "r") as final:
            return json.load(final)
    except FileNotFoundError:
        print("File wallets.json not found.")
        return []
    except:
        print("Errors with wallets.json file.")
        return []

wallets = loadWallets()

async def getWallets():
    return wallets

async def addWallet(wallet):
    wallets.append(wallet)

async def deleteWallet(id):
    wallets.pop(id)

async def editWallet(id, data):
    wallets[id] = data

async def saveWalletsDB():
    with open("wallets.json", "w") as final:
	    json.dump(wallets, final)

async def walletNames() -> list[str]:
    wallets = await getWallets()
    list_of_names = list(map(lambda i: i['name'], wallets))
    return list_of_names

class EditWalletProcess():
    
    def __init__(self) -> None:
        self.step = 1

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:

        match self.step:
            case 1: 
                wallet_names = await walletNames()
                reply = [wallet_names]

                reply.append(['Отмена'])
            
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите кошелек, который нужно изменить:', reply_markup=markup)
                
                self.step += 1
                return False
            case 2:
                wallet_names = await walletNames()
                
                index = 0
                for i in wallet_names:

                    if user_response == i:
                        reply = [
                            ['1','2'],
                            ['Отмена']
                        ]           
                        markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                        self.walletId = index

                        await update.message.reply_text('Выберите что изменить:\n1.Название\n2.Реквизиты\n\n', reply_markup=markup)
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
                        await update.message.reply_text('Введите новые реквизиты:', reply_markup=markup)
                        self.item = 2
                        self.step += 1
                        return False
                    case _:
                        await admin.invalid_reply(update, context)
                        return False
            case _:
                wallets = await getWallets()
                wallet = wallets[self.walletId]
                match self.item:
                    case 1: 
                        wallet['name'] = user_response
                    case 2:
                        wallet['details'] = user_response
                    case _:
                        exception('Incorrect item changing.')

                await editWallet(self.walletId, wallet)
                return True                

               
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        wallet = (await getWallets())[self.walletId]
        await update.message.reply_text('Кошелек был изменен!\nНазвание: {}\nРеквизиты: {}\n'.format(wallet['name'], wallet['details']))
        await saveWalletsDB()

class DeleteWalletProcess():
    
    def __init__(self) -> None:
        self.step = 0

    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str | None) -> bool:
    
        self.step += 1

        match self.step:
            case 1: 
                wallet_names = await walletNames()
                reply = [wallet_names]

                reply.append(['Отмена'])
            
                markup = ReplyKeyboardMarkup(reply, resize_keyboard=True)

                await update.message.reply_text('Выберите кошелек, который нужно удалить', reply_markup=markup)
                return False
            case _:
                wallet_names = await walletNames()
                
                index = 0
                for i in wallet_names:

                    if user_response == i:
                        await deleteWallet(index)
                        return True

                    index += 1
 
                await admin.invalid_reply(update, context)
                return False
               
    async def finalize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        await update.message.reply_text('Кошелек был удален!')

        await saveWalletsDB()

class AddWalletProcess():
    
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

                if user_response in await walletNames():
                    await update.message.reply_text('Такой кошелек уже добавлен.\nВведите другое имя', reply_markup=markup)
                    return False

                self.step += 1
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
    
        await saveWalletsDB()

class Wallets():
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply = [
            ['Cписок кошельков'],
            ['Добавить', 'Удалить', 'Изменить'],
            ['Отмена'],
        ]

        markup = ReplyKeyboardMarkup(reply)
        await update.message.reply_text('Меню настройки кошельков', reply_markup=markup)

    @staticmethod
    async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
        
        user_response = update.message.text

        if user_response == 'Отмена':
            admin.adminInstance.local_state = None
            
            admin.adminInstance.state = admin.Idle
            await admin.adminInstance.finishedState(update, context)

        elif user_response == 'Cписок кошельков':
            text = 'Список кошельков: '
            j = 0
            for i in await getWallets():
                j += 1
                text += '\n' + str(j) + '.' + i['name'] + " - " + i['details']

            await update.message.reply_text(text)
            await Wallets.start(update, context)

        elif user_response == 'Добавить':
            local_state = AddWalletProcess()
            admin.adminInstance.local_state = local_state
            await local_state.run(update, context, None)
              
        elif user_response == 'Удалить':
            local_state = DeleteWalletProcess()
            admin.adminInstance.local_state = local_state
            await local_state.run(update, context, None)

        elif user_response == 'Изменить':
            local_state = EditWalletProcess()
            admin.adminInstance.local_state = local_state
            await local_state.run(update, context, None)
        elif user_response == 'Сохранить в базу':
            await saveWalletsDB()
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
                print(wallets)
