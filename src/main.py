import signal, sys
from logging import error 
from os import getenv
from typing import Dict, List, final
from dotenv import load_dotenv
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes, JobQueue, MessageHandler, filters
from telegram import Message, MessageAutoDeleteTimerChanged, Update
import logging
import admin, client

load_dotenv()

try:
    TOKEN = getenv("BOT_TOKEN")
except: 
    error('Token not provided in .env')
    quit()

try:
    ADMIN_ID = int(getenv("ADMIN_ID"))
except:
    error('Admin ID not provided in .env')
    quit()

try:
    TECHNICIAN_ID = int(getenv("TECHNICIAN_ID"))
except:
    error('Technician ID not provided in .env')
    quit()

from telegram.ext import ApplicationBuilder

app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    user = update.message.chat.id
    if user == ADMIN_ID: 
        await admin.start(update, context)
    else:
        logging.info(f"User requested 'start' command: {update.message.chat}")
        if user in await admin.blockedUserIDs():
            text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите' + admin.adminInstance.username
            await update.message.reply_text(text)
            return 

        await client.start(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.chat.id
    if user == ADMIN_ID: 
        await admin.handle_reply(update, context)
    else:
        if user in await admin.blockedUserIDs():
            text = 'Вы были заблокированы.⛔️\nЕсли у вас остались вопросы, напишите' + admin.adminInstance.username
            await update.message.reply_text(text)
            return 
        
        await client.handle_reply(update, context)

async def button_handler(update: Update, context: CallbackContext) -> None:
    await admin.button_handler(update, context)

async def technical_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    userId = update.message.chat.id
    if userId == TECHNICIAN_ID:
        await admin.adminInstance.technicalJobOnOff()
         
        await admin.technicianInstance.afterTechnicalButton(update, context) 
        

async def run_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    userId = update.message.chat.id
    if userId == TECHNICIAN_ID:

        #for key in admin.adminInstance.requests:
        #    admin.adminInstance.requests[key].shown_to_admin = False

        await admin.adminInstance.runRequests(update, context)

def handle_exit(signum, frame):
    print(f"Received signal {signum}, saving requests...")
    
    admin.saveRequests(admin.adminInstance.requests, "requests.pkl")
    admin.saveRequests(admin.technicianInstance.messages, "technical_messages.pkl")

    sys.exit(0)

def main() -> None:
    try:
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)

        app.add_handler(CommandHandler('start', start));
        app.add_handler(CommandHandler('technical_jobs', technical_jobs));
        app.add_handler(CommandHandler('run_requests', run_requests));
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_reply))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except:
        handle_exit(None, None)
    finally:
        handle_exit(None, None)


if __name__ == "__main__":
    main()


#remember
#id
#first name, last name
#details
