import json
import asyncio

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputFile, MediaGroup
from emoji import emojize
from copy import copy

import async_db_crud
import bot_logic
import python_object_tables
from bot_logic import ClassUser, bot, message_response
from loguru import logger


async def get_step_data(step_id: int) -> tuple[dict, InlineKeyboardMarkup, dict]:
    """
    return all info needed from table steps
    step_data -- raw info. all the info from table steps for this step_id
    type -- a type of step. possible values: choosing, closed_question, final_training, open_question,
    stickersgifs, teacher_reaction, theory
    step_text -- bot uses it to generate text for a message
    answer_text -- if there is only one answer correct possible for this step, bot uses this field
    answer_json -- if there are various correct answers, bot uses this field
    step_text_with_answer -- this field contains question with the answer embedded.
    if user did a lot of mistakes with this question, bot sends him this text
    :param step_id:
    :return: tuple[str, dict, InlineKeyboardMarkup, dict] своими словами каждый параметр
    """
    # record = await async_db_crud.steps.select(f"type, step_text, answer_text, answer_json, step_text_with_answer "
    #                                           f"from dbo.steps "
    #                                           f"where id = {step_id}::INTEGER "
    #                                           f"and actual = True "
    #                                           f"order by dadd desc "
    #                                           f"limit 1",
    #                                           'fetchone')

    # step_data = [record['type'], record['step_text'], record['answer_text'],
    #              json.loads(record['answer_json']) if record['answer_json'] is not None else record['answer_json'],
    #              record['step_text_with_answer']]

    # step_data_dict = {'type': step_data[0], 'step_text': str(step_data[1]).replace("\\n", "\n"),
    #                   'answer_text': step_data[2], 'answer_json': step_data[3],
    #                   'step_text_with_answer': str(step_data[4]).replace("\\n", "\n")}

    step_data_dict = python_object_tables.steps_dict[step_id]

    step_kb = None
    step_answers_dict = {}
    if step_data_dict['answer_json'] is not None and step_data_dict['type'] in (
            'choosing', 'theory', 'closed_question', 'portioning', 'need_help'):
        step_kb = InlineKeyboardMarkup(row_width=1)
        #numbers = list(range(0, len(step_data_dict)))
        #i = iter(numbers)
        i=0
        for answer in step_data_dict['answer_json']:
            answer_key = i
            i+=1
            step_kb.add(InlineKeyboardButton(text=answer, callback_data=str(answer_key)))
            step_answers_dict[answer_key] = answer

    return step_data_dict, step_kb, step_answers_dict


async def set_user_id_from_tg(message) -> int:
    """
    this func takes a message from user on input and sets user_id param to ClassUser
    :param message:
    :return user_id:
    """
    user_tg_id = message.chat.id

    if not await async_db_crud.users_tg.check_id(id=user_tg_id):
        user_id = (await async_db_crud.users.select(f"case when max(id) is null then 1 else max(id)+1 end "
                                                    f"from dbo.users",
                                                    fetch_type='fetchone'))['case']
        await async_db_crud.users.insert(f"({user_id}, '{message.from_user.first_name}','{message.from_user.last_name}')")
        await async_db_crud.users_tg.insert(
                                            f"( '{user_tg_id}', "
                                            f"'{message.from_user.first_name}',"
                                            f"'{message.from_user.last_name}', "
                                            f"{user_id}, "
                                            f"'{message.from_user.username}', "
                                            f"{True if message.from_user.is_premium is not None else False})")
    else:
        user_id = (await async_db_crud.users_tg.select(f"user_id "
                                                       f"from dbo.users_tg "
                                                       f"where id = {user_tg_id}::BIGINT "
                                                       f"and actual = True "
                                                       f"order by dadd desc "
                                                       f"limit 1",
                                                       fetch_type='fetchone'))['user_id']

    return user_id


async def lessons_first_step(lesson_id: int) -> int:
    """
    this func returns step_id for the first(start) step from lesson provided
    :param lesson_id:
    :return step_id:
    """
    # return (await async_db_crud.routs_catalog.select(f"object_id "
    #                                                  f"from dbo.routs_catalog "
    #                                                  f"where entity_type = 'lessons' "
    #                                                  f"and entity_id = {lesson_id}::INTEGER "
    #                                                  f"and object_type = 'step' "
    #                                                  f"and connection_type = 'start' "
    #                                                  f"and actual = True "
    #                                                  f"order by dadd desc "
    #                                                  f"limit 1",
    #                                                  fetch_type='fetchone'))['object_id']
    return python_object_tables.lessons_start_and_repeat_step_id_dict[lesson_id]['start']


async def lessons_current_step(user_id: int, lesson_id: int) -> int:
    """
    if this user has an actual step for this lesson, a func returns actual step's step_id
    if this user doesn't have actual step for this lesson, a func return step with type 'start' or 'retry_lesson'
    :param user_id:
    :param lesson_id:
    :return step_id:
    """
    lessons_current_step_data = (await async_db_crud.user_progress.select(f"object_id "
                                                                          f"from dbo.user_progress "
                                                                          f"where user_id = {user_id}::BIGINT "
                                                                          f"and entity_type = 'lessons' "
                                                                          f"and entity_id = nullif('{lesson_id}', 'None')::INTEGER "
                                                                          f"and object_type = 'step' "
                                                                          f"and actual = True "
                                                                          f"order by dadd desc "
                                                                          f"limit 1",
                                                                          fetch_type='fetchone'))
    if lessons_current_step_data is not None:
        lessons_current_step_result = lessons_current_step_data['object_id']
    else:
        lessons_current_step_result = lessons_first_step(lesson_id)

    return lessons_current_step_result


async def get_levels_data() -> tuple[InlineKeyboardMarkup, dict]:
    # levels_list = await async_db_crud.levels.select("name, id "
    #                                                 "from dbo.levels "
    #                                                 "where actual = True "
    #                                                 "order by row_order")
    levels_list = python_object_tables.levels_list
    levels_kb = InlineKeyboardMarkup(row_width=1)
    levels_dict = {}
    for level in levels_list:
        levels_kb.add(InlineKeyboardButton(text=level[0], callback_data=level[1]))
        levels_dict[level[1]] = level[0]

    return levels_kb, levels_dict


async def get_lessons_data(level_id):

    # lessons_list = await async_db_crud.lessons.select(f"name, id "
    #                                                   f"from dbo.lessons "
    #                                                   f"where level_id = {level_id}::INTEGER "
    #                                                   f"and actual = True "
    #                                                   f"order by id")
    lessons_list = []
    if level_id in python_object_tables.lessons_dict:
        lessons_list = python_object_tables.lessons_dict[level_id]

    lessons_kb = InlineKeyboardMarkup(row_width=1)
    lessons_dict = {}
    for lesson in lessons_list:
        lessons_kb.add(InlineKeyboardButton(text=lesson[0], callback_data=lesson[1]))
        lessons_dict[lesson[1]] = lesson[0]

    return lessons_kb, lessons_dict


async def set_user_progress_data(user_id: int, lesson_id: int, step_id: int, answer_text: str, correct: bool) -> None:

    await async_db_crud.user_progress.special_update(answer_text, correct,
                                                     f"user_id = {user_id}::BIGINT and "
                                                     f"entity_type = 'lessons' and "
                                                     f"entity_id = {lesson_id}::INTEGER "
                                                     f"and object_type = 'step' "
                                                     f"and object_id = {step_id}::INTEGER "
                                                     f"and actual = True")

    # record = (await async_db_crud.user_progress.select("* "
    #                                                    "from dbo.user_progress "
    #                                                    f"where user_id = {user_id}::BIGINT and "
    #                                                    f"entity_type = 'lessons' and "
    #                                                    f"entity_id = {lesson_id}::INTEGER "
    #                                                    f"and object_type = 'step' "
    #                                                    f"and object_id = {step_id}::INTEGER "
    #                                                    f"and actual = True",
    #                                                    'fetchone'))
    #
    # while record['answer_text'] != answer_text:
    #
    #     await async_db_crud.user_progress.special_update(answer_text, correct,
    #                                                      f"user_id = {user_id}::BIGINT and "
    #                                                      f"entity_type = 'lessons' and "
    #                                                      f"entity_id = {lesson_id}::INTEGER "
    #                                                      f"and object_type = 'step' "
    #                                                      f"and object_id = {step_id}::INTEGER "
    #                                                      f"and actual = True")
    #
    #     record = (await async_db_crud.user_progress.select("* "
    #                                                        "from dbo.user_progress "
    #                                                        f"where user_id = {user_id}::BIGINT and "
    #                                                        f"entity_type = 'lessons' and "
    #                                                        f"entity_id = {lesson_id}::INTEGER "
    #                                                        f"and object_type = 'step' "
    #                                                        f"and object_id = {step_id}::INTEGER "
    #                                                        f"and actual = True",
    #                                                        'fetchone'))
    #
    #     await asyncio.sleep(0.25)


async def is_start_lesson(user_id: int, lesson_id: int) -> bool:
    """
    If this user doesn't actual step in this lesson, we put him on status 'star' or 'repeat_lesson'
    'start' -- if this user hasn't finished this lesson yet
    'repeat_lesson' -- if he finished this lesson in the past, and now he wants to learn it again
    :param lesson_id:
    :param user_id:
    :return: None
    """

    # if True, then user even has never started this lesson, or he'd started and finished it
    if (await async_db_crud.user_progress.select(f"count(*) "
                                                 f"from dbo.user_progress "
                                                 f"where user_id = {user_id}::BIGINT "
                                                 f"and entity_type = 'lessons' "
                                                 f"and entity_id = {lesson_id}::INTEGER "
                                                 f"and object_type = 'step' "
                                                 f"and actual = True",
                                                 'fetchone'))['count'] == 0:

        if (await async_db_crud.user_finished_lessons.select(f"count(*)"
                                                             f"from dbo.user_finished_lessons "
                                                             f"where user_id = {user_id}::BIGINT "
                                                             f"and lesson_id = {lesson_id}::INTEGER "
                                                             f"and actual = True",
                                                             'fetchone'))['count'] > 0:
            next_step_connection_type = 'repeat_lesson'
        else:
            next_step_connection_type = 'start'

        # next_step_id = (await async_db_crud.user_progress.select(f"object_id "
        #                                                          f"from dbo.routs_catalog "
        #                                                          f"where user_id is null "
        #                                                          f"and entity_type = 'lessons' "
        #                                                          f"and entity_id = {lesson_id}::INTEGER "
        #                                                          f"and object_type = 'step' "
        #                                                          f"and connection_type = '{next_step_connection_type}' "
        #                                                          f"and actual = True "
        #                                                          f"order by dadd "
        #                                                          f"desc limit 1",
        #                                                          'fetchone'))['object_id']
        next_step_id = python_object_tables.lessons_start_and_repeat_step_id_dict[lesson_id][next_step_connection_type]

        await ClassUser.set_step_id(user_id, next_step_id)
        ClassUser.connection_type = 'start'

        return True

    else:
        return False


async def delete_inline_keyboard_from_last_bot_message(this_chat_id: int) -> None:
    if (await async_db_crud.tg_message_log.select(f"count(*) "
                                                  f"from dbo.tg_message_log "
                                                  f"where chat_id = {this_chat_id}::BIGINT  "
                                                  f"and is_bot = True "
                                                  f"and has_inline_keyboard = True",
                                                  fetch_type='fetchone'))['count'] != 0:

        record = (await async_db_crud.tg_message_log.select(f"message_id, has_inline_keyboard "
                                                            f"from dbo.tg_message_log "
                                                            f"where chat_id = {this_chat_id}::BIGINT  "
                                                            f"and is_bot = True "
                                                            f"order by dadd desc "
                                                            f"limit 1",
                                                            fetch_type='fetchone'))

        last_message_from_bot_id = record['message_id']
        last_message_from_bot_has_inline_keyboard = record['has_inline_keyboard']

        if last_message_from_bot_has_inline_keyboard:
            asyncio.create_task(async_db_crud.tg_message_log.update("has_inline_keyboard = False",
                                                                    f"chat_id = {this_chat_id}::BIGINT and "
                                                                    f"message_id = {last_message_from_bot_id}::BIGINT"
                                                                    ))
            try:
                await bot.edit_message_reply_markup(chat_id=this_chat_id, message_id=last_message_from_bot_id,
                                                    reply_markup=None)
            except:
                pass


async def send_message_photo(user_tg_id, text, reply_markup, parse_mode, step_id) -> int:
    """
    custom func for sending messages to user
    if we want to send only text message,  we use bot.send_message
    if we want to send text message with 1 photo, we use bot.send_photo
    if we want to send text message with more than 1 photo, we use bot.send_media_group
    :param user_tg_id:
    :param text:
    :param reply_markup:
    :param parse_mode:
    :param step_id:
    :return message_id:
    """

    # photo_array = await async_db_crud.files.select("concat(python_package_name,'/',file_name) "
    #                                                "from dbo.files "
    #                                                f"where step_id = {step_id}::INTEGER")
    photo_array = []
    if step_id in python_object_tables.files_dict:
        photo_array = python_object_tables.files_dict[step_id]

    if len(photo_array) == 0:
        msg = await bot.send_message(chat_id=user_tg_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        msg_copy = copy(msg)
        return msg_copy.message_id
    elif len(photo_array) == 1:
        photo_path = photo_array[0]
        photo_bytes = InputFile(path_or_bytesio=photo_path)
        msg = await bot.send_photo(chat_id=user_tg_id,
                                   photo=photo_bytes,
                                   reply_markup=reply_markup,
                                   caption=text,
                                   parse_mode=parse_mode)
        msg_copy = copy(msg)
        return msg_copy.message_id
    else:
        album = MediaGroup()

        photo_bytes = InputFile(path_or_bytesio=photo_array[0])
        album.attach_photo(photo_bytes, caption=emojize(text), parse_mode='HTML')

        for ph in photo_array[1::]:
            photo_bytes = InputFile(path_or_bytesio=ph)
            album.attach_photo(photo_bytes)

        msg = await bot.send_media_group(chat_id=user_tg_id, media=album)
        msg_copy = copy(msg)

        return msg_copy[0].message_id


async def is_end_lesson(user_id: int, lesson_id: int, next_step_data: list, message):
    """
    if next_step_data is None -- that means we reached the end of this lesson
    so, we have to start this lesson again, but not from 'start' step, but from 'repeat_lesson' step
    also we have to mark this lesson as finished for this ClassUser. for this we make an insert to user_finished_lessons table
    notice, that for each user-lesson condition we have 1 row maximum in user_finished_lessons table
    :param user_id:
    :param lesson_id:
    :param next_step_data:
    :param message:
    :return:
    """
    if not next_step_data:
        # step_id = (await async_db_crud.user_progress.select(f"object_id "
        #                                                     f"from dbo.routs_catalog "
        #                                                     f"where user_id is null "
        #                                                     f"and entity_type = 'lessons' "
        #                                                     f"and entity_id = {lesson_id}::INTEGER "
        #                                                     f"and object_type = 'step' "
        #                                                     f"and connection_type = 'repeat_lesson' "
        #                                                     f"and actual = True "
        #                                                     f"order by dadd desc limit 1",
        #                                                     'fetchone'))['object_id']
        step_id = python_object_tables.lessons_start_and_repeat_step_id_dict[lesson_id]['repeat_lesson']
        await ClassUser.set_step_id(user_id, step_id)

        if (await async_db_crud.user_finished_lessons.select(f"count(*)"
                                                             f"from dbo.user_finished_lessons "
                                                             f"where user_id = {user_id}::BIGINT "
                                                             f"and lesson_id = {lesson_id}::INTEGER "
                                                             f"and actual = True",
                                                             'fetchone'))['count'] == 0:
            await async_db_crud.user_finished_lessons.insert(f"({user_id}, {lesson_id})")

        await ClassUser.set_status(user_id, 2)
        await message_response(message, old_messages_ignore=True)


async def get_error_effort_count(user_id: int, step_id: int) -> int:
    if (await async_db_crud.error_effort_count.select("count(*) "
                                                      "from dbo.error_effort_count "
                                                      f"where user_id = {user_id} "
                                                      f"and step_id = {step_id}",
                                                      'fetchone'))['count'] == 0:
        await async_db_crud.error_effort_count.insert(f"({user_id}, {step_id}, 0)")
        return 0
    else:
        return (await async_db_crud.error_effort_count.select("err_count "
                                                              "from dbo.error_effort_count "
                                                              f"where user_id = {user_id} "
                                                              f"and step_id = {step_id}",
                                                              'fetchone'))['err_count']


async def go_to_next_step(error_count: int, user_id: int, lesson_id: int, previous_question_id: int, message):

    if error_count > 0:
        await async_db_crud.error_effort_count.update(f"err_count = 0 ",
                                                      f"user_id = {user_id} and step_id = {previous_question_id}")

    record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                                                      f"from dbo.routs_catalog "
                                                      f"where user_id is null "
                                                      f"and connection_type = 'mandatory' "
                                                      f"and parent_object_id = {previous_question_id}::INTEGER "
                                                      f"and entity_type = 'lessons' "
                                                      f"and entity_id = {lesson_id}::INTEGER "
                                                      f"and actual = True "
                                                      f"order by dadd desc limit 1",
                                                      'fetchone')

    if record is not None:
        next_step_data = [record['object_id'], record['connection_type']]
    else:
        next_step_data = []

    await is_end_lesson(user_id, lesson_id, next_step_data, message)
    if next_step_data:
        await ClassUser.set_step_id(user_id, next_step_data[0])
        ClassUser.connection_type = next_step_data[1]
        #await bot_logic.message_response(message, old_messages_ignore=True)


async def get_next_step_data(step_id: int, lesson_id: int) -> list:
    step_data_dict = python_object_tables.steps_dict[step_id]
    # if len(step_data_dict['next_step_data']) == 1:
    if isinstance(step_data_dict['next_step_data'], int):
        step_id = int(step_data_dict['next_step_data'])
        # connection_type = step_data_dict['next_step_data'][step_id]
        connection_type = 'mandatory' # if isinstance(step_data_dict['next_step_data'], int) else 'optional'
        next_step_data = [step_id, connection_type]
    else:
        record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                                                          f"from dbo.routs_catalog "
                                                          f"where user_id is null "
                                                          f"and connection_type = 'mandatory' "
                                                          f"and parent_object_id = {step_id}::INTEGER "
                                                          f"and entity_type = 'lessons' "
                                                          f"and entity_id = {lesson_id}::INTEGER "
                                                          f"and actual = True "
                                                          f"order by dadd desc limit 1",
                                                          'fetchone')

        if record is not None:
            next_step_data = [record['object_id'], record['connection_type']]
        else:
            next_step_data = []

    return next_step_data


rkm = ReplyKeyboardMarkup(resize_keyboard=True)
rkm.add(KeyboardButton(emojize(':blue_book:levels')))
rkm.add(KeyboardButton(emojize(':notebook_with_decorative_cover:lessons')))
rkm.add(KeyboardButton(emojize(':open_book:start_lesson_from_beginning')))
