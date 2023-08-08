import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import token, chat_id
from pyrogram import Client
import asyncio
import datetime
import itertools
import aiogram.utils.executor
import pytz
from config import api_id, api_hash
from keywords import keywords
from chat_links import chat_links


# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the bot and dispatcher objects
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())


# Инициализация планировщика
scheduler = AsyncIOScheduler()
scheduler.start()


async def get_author_info(client, chat_id, user_id):
    try:
        user = await client.get_users(user_id)
        return f"{user.first_name} {user.last_name} ({user.username})", f"https://t.me/{user.username}"
    except:
        return None, None


async def fetch_messages_from_chats(chat_links, keywords):
    # Create a new Pyrogram client
    client = Client("my_session")

    # Log in to the client
    async with client:

        parsed_messages = []
        # Initialize start time

        # Get current date
        current_date = datetime.date.today()

        # Iterate over each chat link and fetch messages containing keywords
        for link in chat_links:
            try:
                # Extract the chat username or ID from the link
                chat_identifier = link.split("/")[-1]

                # Fetch the chat information
                try:
                    chat = await client.get_chat(chat_identifier)
                except:
                    print(f"Skipping chat link: {link}. User is not a member of the chat.")
                    continue
                chat_id = chat.id

                # Fetch messages containing the keywords in the chat
                for keyword in keywords:

                    async for message in client.search_messages(chat_id, keyword):
                        # Rest of the code to process each message goes here

                        # Write messages to the worksheet
                        #for message in messages:
                        # Check if the message is from today
                        if message.date.date() == current_date:
                            date_time = message.date.strftime("%Y-%m-%d %H:%M:%S")

                            # Get author info
                            author_name, author_link = await get_author_info(client, chat_id, message.from_user.id)

                            parsed_message = {
                                "chat": chat.title,
                                "link": link,
                                "author": author_name,
                                "author_link": author_link,
                                "date_time": date_time,
                                "keywords_used": [keyword],
                                "message_text": message.text,
                            }
                            # Проверяем, что текст сообщения не пустой
                            if parsed_message["message_text"]:
                                parsed_messages.append(parsed_message)

                # Sleep for 2 seconds between iterations
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error processing chat link: {link}")
                print(f"Error message: {str(e)}")
                print()
                continue
    return parsed_messages


# Uncomment and adjust the scheduling code
async def schedule_fetch_and_forward():
    while True:
        # Get the current time in the user's timezone (you can adjust the timezone as needed)
        tz = pytz.timezone('Europe/Moscow')  # 'Europe/Moscow' is the timezone for Moscow
        current_time = datetime.datetime.now(tz)

        # Define the times for message fetching and forwarding (adjust the times as needed)
        fetch_times = [datetime.time(15, 0)]

        if current_time.time() in fetch_times:
            try:
                parsed_messages = await fetch_messages_from_chats(chat_links, keywords)
                await send_message_to_user(chat_id, parsed_messages)  # Send the messages directly here
            except Exception as e:
                print(f"Error occurred during scheduled fetch and forward: {str(e)}")

        # Sleep for 1 minute to avoid continuous checking
        await asyncio.sleep(60)


# Функция, которая будет выполняться по расписанию
async def job_function(chat_id, messages):

    if not messages:
        await bot.send_message(chat_id, "No messages found.")
        return

    message_chunk_size = 4096  # Maximum message size limit for Telegram

    message_to_send = "Messages found:\n\n"
    for message in messages:
        message_info = (
            f"Chat: {message['chat']}\n"
            f"Chat_link: {message['link']}\n"
            f"Author: {message['author']} ({message['author_link']})\n"
            f"Date: {message['date_time']}\n"
            f"Keywords: {', '.join(message.get('keywords_used', []))}\n\n"
            f"Message: {message['message_text']}\n\n"
        )

        # Check if the chunk size exceeds the limit and split the message if necessary
        if len(message_to_send) + len(message_info) <= message_chunk_size:
            message_to_send += message_info
        else:
            # Send the current chunk
            await bot.send_message(chat_id, message_to_send)

            # Start a new chunk
            message_to_send = message_info

    # Send any remaining messages in the last chunk
    await bot.send_message(chat_id, message_to_send)


# Function to send messages to the user using the bot
async def send_message_to_user(chat_id, messages):
    if not messages:
        await bot.send_message(chat_id, "No messages found.")
        return

    message_chunk_size = 4096  # Maximum message size limit for Telegram

    message_to_send = "Messages found:\n\n"
    for message in messages:
        # Форматирование текста ключевых слов
        formatted_keywords = ", ".join([f"<b>{kw}</b>" for kw in message.get("keywords_used", [])])

        message_info = (
            f"Chat: {message['chat']}\n"
            f"Chat_link: {message['link']}\n"
            f"Author: {message['author']} ({message['author_link']})\n"
            f"Date: {message['date_time']}\n"
            f"Keywords: {formatted_keywords}\n\n"
            f"Message: {message['message_text']}\n"
        )

        # Check if the chunk size exceeds the limit and split the message if necessary
        if len(message_to_send) + len(message_info) <= message_chunk_size:
            message_to_send += message_info
        else:
            # Send the current chunk
            await bot.send_message(chat_id, message_to_send, parse_mode="HTML")

            # Start a new chunk
            message_to_send = message_info

    # Send any remaining messages in the last chunk
    await bot.send_message(chat_id, message_to_send, parse_mode="HTML")


# Handler for the /start command
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    # Запуск планировщика при старте бота
    scheduler.add_job(lambda: job_function(message.from_user.id, []), 'interval', hours=6)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton(text="/fetch_messages"),
        types.KeyboardButton(text="Help"),
    ]
    keyboard_markup.add(*buttons)
    welcome_message = "Welcome to the telegram bot. For help, press the Help command."
    await bot.send_message(message.from_user.id, welcome_message, reply_markup=keyboard_markup)


# Handler for the /fetch_messages command
@dp.message_handler(commands=['fetch_messages'])
async def fetch_messages_command(message: types.Message):
    try:
        # Add the "Request in progress. Please wait" message here
        await bot.send_message(message.from_user.id, "Request in progress. Please wait")

        # Call the fetch_messages_from_chats function using await
        parsed_messages = await fetch_messages_from_chats(chat_links, keywords)
        # Send the result to the user
        await send_message_to_user(message.from_user.id, parsed_messages)
    except Exception as e:
        await bot.send_message(message.from_user.id, f"Error occurred: {str(e)}")


# Handler for the "Help" button
@dp.message_handler(lambda message: message.text == "Help")
async def help(message: types.Message):
    await message.answer("Help using the bot:\n"
                         "1. /start command - start the bot\n"
                         "2. '/fetch_messages' button - receive messages from chats\n"
                         "3. 'Help' button - displaying help information")


@dp.message_handler()
async def handle_unknown_command(message: types.Message):
    await message.answer("The bot does not know this command. See the help team")


# Modify the run_bot function
async def run_bot():
    try:
        loop = asyncio.get_event_loop()

        # Create a task for the scheduling function
        loop.create_task(schedule_fetch_and_forward())

        # Start the dispatcher
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()


# Start the bot
if __name__ == '__main__':
    asyncio.run(run_bot())
