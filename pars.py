from pyrogram import Client
import xlsxwriter
import time
import datetime
from config import api_id, api_hash
from keywords import keywords
from chat_links import chat_links


def get_author_info(client, chat_id, user_id):
    try:
        user = client.get_users(user_id)
        return f"{user.first_name} {user.last_name} ({user.username})", f"https://t.me/{user.username}"
    except:
        return None, None


def fetch_messages_from_chats(chat_links, keywords):
    # Create a new Pyrogram client
    client = Client("my_session")

    # Create a new Excel workbook and worksheet
    workbook = xlsxwriter.Workbook('messages.xlsx')
    worksheet = workbook.add_worksheet()

    # Write headers to the worksheet
    worksheet.write_row(0, 0, ["Чат", "Ссылка на чат", "Автор", "Ссылка на автора", "Дата и время", "Текст сообщения"])

    # Initialize row counter
    row = 1

    # Log in to the client
    with client:

        # Initialize start time
        start_time = time.time()

        # Get current date
        current_date = datetime.date.today()

        # Iterate over each chat link and fetch messages containing keywords
        for link in chat_links:
            try:
                # Extract the chat username or ID from the link
                chat_identifier = link.split("/")[-1]

                # Fetch the chat information
                try:
                    chat = client.get_chat(chat_identifier)
                except:
                    print(f"Skipping chat link: {link}. User is not a member of the chat.")
                    continue
                chat_id = chat.id

                # Fetch messages containing the keywords in the chat
                for keyword in keywords:

                    messages = client.search_messages(chat_id, keyword)

                    # Write messages to the worksheet
                    for message in messages:
                        # Check if the message is from today
                        if message.date.date() == current_date:
                            date_time = message.date.strftime("%Y-%m-%d %H:%M:%S")

                            # Get author info
                            author_name, author_link = get_author_info(client, chat_id, message.from_user.id)

                            worksheet.write(row, 0, chat.title)
                            worksheet.write(row, 1, link)  # Add the chat link
                            worksheet.write(row, 2, author_name if author_name else "None")
                            worksheet.write(row, 3, author_link if author_link else "None")
                            worksheet.write(row, 4, date_time)
                            worksheet.write(row, 5, message.text)
                            row += 1

                            # Print the received data
                            print(f"Chat: {chat.title}")
                            print(f"Chat Link: {link}")
                            print(f"Author: {author_name if author_name else 'None'}")
                            print(f"Author Link: {author_link if author_link else 'None'}")
                            print(f"Date and Time: {date_time}")
                            print(f"Message Text: {message.text}")
                            print()

                # Sleep for 2 seconds between iterations
                time.sleep(2)

            except Exception as e:
                print(f"Error processing chat link: {link}")
                print(f"Error message: {str(e)}")
                print()
                continue

    # Close the workbook
    workbook.close()
    # Сообщение о записи данных в файл
    print("All data has been written to messages.xlsx")
    # Calculate execution time
    execution_time = time.time() - start_time
    print(f"Execution time: {execution_time} seconds")


# Call the function
fetch_messages_from_chats(chat_links, keywords)
