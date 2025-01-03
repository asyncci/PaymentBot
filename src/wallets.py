from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import admin, json


wallets = []

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
                match user_response:
                    case '1':
                        await update.message.reply_text('Введите новое название:')
                        self.item = 1
                        self.step += 1
                        return False
                    case '2':
                        await update.message.reply_text('Введите новые реквизиты:')
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

        elif user_response == 'Cписок кошельков':
            text = 'Список кошельков: '
            j = 0
            for i in await getWallets():
                j += 1
                text += '\n' + str(j) + '.' + i['name']

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
            local_state = EditWalletProcess()
            context.user_data['local_state'] = local_state
            await local_state.run(update, context, None)
        elif user_response == 'Сохранить в базу':
            await saveWalletsDB()
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
                await Wallets.pickAction(update, context)
                print(wallets)