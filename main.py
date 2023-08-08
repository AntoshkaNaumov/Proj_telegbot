import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aioschedule
from config import token, chat_id
from pyrogram import Client
import asyncio
import datetime
import aiogram.utils.executor
from keywords import keywords
from chat_links import chat_links

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the bot and dispatcher objects
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())


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


async def fetch_messages_job():
    try:
        parsed_messages = await fetch_messages_from_chats(chat_links, keywords)
        await send_message_to_user(chat_id, parsed_messages)
    except Exception as e:
        print(f"Error occurred in fetch_messages_job: {str(e)}")


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
    keyboard_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton(text="/fetch_messages"),
        types.KeyboardButton(text="Help"),
    ]
    keyboard_markup.add(*buttons)
    welcome_message = "Welcome to the telegram bot. See the help command."
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


# Запуск бота
async def run_bot():
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()


# Запуск основной функции бота в асинхронном режиме
if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # Инициализация планировщика
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')

    # Запуск функции fetch_messages_job каждый час
    scheduler.add_job(fetch_messages_job, 'interval', hours=1)
    
    # Запуск планировщика
    scheduler.start()

    loop.run_until_complete(run_bot())
