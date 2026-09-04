from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
import re
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
import os
from flask import Flask
import threading

web = Flask(__name__)

def runFlask():
   web.run(debug=False,port=8000,host="0.0.0.0")

flaskThread = threading.Thread(
        target=runFlask,
        daemon=True
)

@web.route('/', methods=['GET', 'POST'])
def home():
    return "<html><body></body></html>"

load_dotenv()
TARGETID = os.getenv("TARGETID")
TOKEN = os.getenv("TOKEN")
REASON, DURATION = range(2)
CONSEQUENCE1 = os.getenv("CONSEQUENCE1")
CONSEQUENCE2 = os.getenv("CONSEQUENCE2")
CONSEQUENCE3 = os.getenv("CONSEQUENCE3")

isTicketActive = False
endTime = 0
reason = ""

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong")

async def createForm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form"] = {}
    await update.message.reply_text(
        "A BitRegistry Session has been instantiated,\n\n"
        f"As per company policy, all 'bits' and 'mos' must be documented with their expiration date requiring all BitMo instances to be ceased under {CONSEQUENCE1} \n\n"
        "Failure to correctly evaluate time constraints is not a valid exemption of BitRegistry \n\n"
        "Please provide your reason for instantiation of BitRegistry"
    )
    return REASON

async def reasonAnswer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form"]["reason"] = update.message.text
    await update.message.reply_text(
        "Please provide the duration of the BitRegistry Session. (HH:MM:SS):"
    )
    return DURATION

async def durationAnswer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    durationText = update.message.text.strip()
    try:
        parsed = datetime.strptime(durationText, "%H:%M:%S")
    except ValueError:
        await update.message.reply_text(
            "Invalid duration.\n\n"
            "Please enter the duration in HH:MM:SS format.\n"
            "Example: `01:30:00`",
            parse_mode="Markdown"
        )
        return DURATION
    duration = timedelta(hours=parsed.hour,minutes=parsed.minute,seconds=parsed.second)

    if duration.total_seconds() <= 0:
        await update.message.reply_text(
            "Duration must be greater than 00:00:00.\n"
            "Please enter the duration again."
        )
        return DURATION
    maxDuration = timedelta(hours=6)

    if duration > maxDuration:
        await update.message.reply_text(
            "Duration cannot exceed 06:00:00.\n"
            "Please enter a shorter duration."
        )
        return DURATION
    context.user_data["form"]["duration"] = duration

    form = context.user_data["form"]

    keyboard = [
        [
            InlineKeyboardButton("Submit", callback_data="submit"),
            InlineKeyboardButton("Cancel", callback_data="cancel"),
        ]
    ]

    await update.message.reply_text(
        f"The following BitRegistry information was recorded:\n\n"
        f"Reason: {form['reason']}\n"
        f"Duration: {form['duration']}\n\n"
        f"Are all fields correct?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END

async def buttonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global isTicketActive
    global reason
    query = update.callback_query
    await query.answer()

    if query.data == "submit":
        form = context.user_data.get("form", {})
        duration  = form.get("duration")
        reason = form.get("reason")

        isTicketActive = True
        asyncio.create_task(
            timerTask(context.application, query.message.chat_id, duration)
        )

        await query.edit_message_text(
            f"BitRegistry has logged a BitMo, noncompliance to cease a BitMo after the expiration time is punishable under {CONSEQUENCE1}"
        )

        context.user_data.pop("form", None)

    elif query.data == "cancel":
        context.user_data.pop("form", None)

        await query.edit_message_text(
            f"The BitRegistry instance is now closing. If this was due to a misfiled ticket, please file a new one. If this was done as a medium of circumventing BitRegistry, {CONSEQUENCE2}"
        )

async def checkMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global isTicketActive
    global endTime
    if update.message.chat.id != TARGETID:
        return ConversationHandler.END

    if not (re.search(r"\b(bit|mo|moment)\b", update.message.text.lower())):
        return

    if isTicketActive:
        await update.message.reply_text(f"A BitRegistry instance is already active, {endTime - datetime.now()} remaining")
        return

    return await createForm(update, context)

async def timerTask(application, chatID, duration):
    global isTicketActive
    global end_time
    global reason
    start_time = datetime.now()
    end_time = start_time + duration
    await asyncio.sleep(duration.total_seconds())
    isTicketActive = False

    await application.bot.send_message(
        chat_id=chatID,
        text=f"Your BitRegistry Session with reason {reason} has expired, \n\n Failure to adhere to one's self imposed time restriction is {CONSEQUENCE3}",
        parse_mode="HTML"
    )


def main():
    flaskThread.start()
    app = (Application.builder().token(TOKEN).build())

    formConversation = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            checkMessage
        )
    ],
        states={
            REASON: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    reasonAnswer
                )
            ],
            DURATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    durationAnswer
                )
            ],
        },
        fallbacks=[]
    )

    app.add_handler(formConversation)
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(buttonHandler))
    print("Logged in")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()