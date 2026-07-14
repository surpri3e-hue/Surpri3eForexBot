from users import get_all_users


async def send_broadcast(bot, text):

    users = get_all_users()


    count = 0


    for user in users:

        try:

            await bot.send_message(
                chat_id=user,
                text=text
            )

            count += 1


        except:

            pass


    return count
