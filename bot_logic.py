import asyncio
import random
from aiogram import Bot, types, Dispatcher, executor
from aiogram.types import ReplyKeyboardRemove, InputFile, MediaGroup
from emoji import demojize, emojize
from asyncio import sleep
from copy import copy
from loguru import logger
import json

import async_db_crud
import python_object_tables
import user_management
import config

logger.add("debug_logs/debug_bot_logic.log",
           format="{time} {level} {message}",
           level="DEBUG",
           rotation="10 KB",
           compression="zip")


class ClassUser:
    user_id = 0
    status = 0
    level_id = 0
    is_new_message = False
    connection_type = ''

    async def set_status(user_id: int, status: int) -> None:
        ClassUser.status = status
        await async_db_crud.users_status.update("actual = False",
                                                f"user_id = {user_id}::BIGINT "
                                                f"and actual = True")
        await async_db_crud.users_status.insert(f"('{user_id}', {status})")

    async def get_status(user_id: int) -> int:
        return (await async_db_crud.users_status.select(f"status_id "
                                                        f"from dbo.users_status "
                                                        f"where user_id = {user_id}::BIGINT "
                                                        f"and actual = True "
                                                        f"order by dadd desc "
                                                        f"limit 1",
                                                        fetch_type='fetchone'))['status_id']  #if 'status' not in self.__dict__ else self.status

    async def set_level_id(user_id: int, level_id: int) -> None:
        await async_db_crud.user_actual_level.update("actual = False",
                                                     f"user_id = {user_id}::BIGINT and "
                                                     f"actual = True")
        if level_id is not None:
            await async_db_crud.user_actual_level.insert(f"({user_id}, {level_id})")

    async def get_level_id(user_id: int) -> int:
        record = (await async_db_crud.levels.select(f"level_id "
                                                    f"from dbo.user_actual_level "
                                                    f"where user_id = {user_id}::BIGINT "
                                                    f"and actual = True "
                                                    f"order by dadd desc "
                                                    f"limit 1",
                                                    fetch_type='fetchone'))  #if 'level_id' not in self.__dict__ else self.level_id
        if record is None:
            return record
        else:
            return record['level_id']

    async def set_lesson_id(user_id, lesson_id: int) -> None:
        level_id = await ClassUser.get_level_id(user_id)
        await async_db_crud.user_actual_level_lesson.update("actual = False",
                                                            f"user_id = {user_id}::BIGINT "
                                                            f"and actual = True")
        if lesson_id:
            await async_db_crud.user_actual_level_lesson.insert(f"({user_id}, {level_id}, {lesson_id})")

    async def get_lesson_id(user_id: int) -> int:
        try:
            return (await async_db_crud.levels.select(f"lesson_id "
                                                      f"from dbo.user_actual_level_lesson "
                                                      f"where user_id = {user_id}::BIGINT "
                                                      f"and actual = True "
                                                      f"order by dadd desc "
                                                      f"limit 1",
                                                      fetch_type='fetchone'))['lesson_id']  #if 'lesson_id' not in self.__dict__ else self.lesson_id
        except:
            return None

    async def set_step_id(user_id: int, step_id: int) -> None:
        lesson_id = await ClassUser.get_lesson_id(user_id)
        await async_db_crud.user_progress.update("actual = False",
                                                 f"user_id = {user_id}::BIGINT and "
                                                 f"entity_type = 'lessons' "
                                                 f"and entity_id = {lesson_id}::INTEGER "
                                                 f"and object_type = 'step' "
                                                 f"and actual = True")
        await async_db_crud.user_progress.insert(
            f"({user_id}, 'lessons', {lesson_id}, 'step', {step_id}, null, null)")

    async def get_step_id(user_id: int) -> int:

        lesson_id = await ClassUser.get_lesson_id(user_id)

        try:
            lessons_current_step_id = await user_management.lessons_current_step(user_id, lesson_id)
            return lessons_current_step_id  #if 'step_id' not in self.__dict__ else self.step_id
        except:
            return None

    @logger.catch()
    async def get_connection_type(user_id: int) -> str:
        lesson_id = await ClassUser.get_lesson_id(user_id)
        select_query = f"s.connection_type "\
                       f"from dbo.user_progress a "\
                       f"inner join dbo.routs_catalog s "\
                       f"on a.actual = true "\
                       f"and s.actual = true "\
                       f"and a.object_type = 'step' "\
                       f"and a.object_id = s.object_id "\
                       f"and s.entity_type = 'lessons' "\
                       f"and s.object_type = 'step' "\
                       f"and a.entity_type = 'lessons' "\
                       f"and a.entity_id = {lesson_id}::INTEGER "\
                       f"where a.user_id = {user_id}::BIGINT  "\
                       f"and s.entity_id = {lesson_id}::INTEGER "\
                       f"order by a.dadd desc "\
                       f"limit 1"
        return (await async_db_crud.user_progress.select(select_query,
                                                         fetch_type='fetchone'))['connection_type']  #if 'connection_type' not in self.__dict__ else self.connection_type


bot = Bot(token=config.bot_token)
dp = Dispatcher(bot)


@logger.catch()
@dp.callback_query_handler()
async def callback_query_response(callback: types.CallbackQuery):
    """
    if a callback was received, this func is for action
    :param callback:
    :return:
    """

    user_tg_id = callback.message.chat.id
    message_id = callback.message.message_id
    user_id = await user_management.set_user_id_from_tg(callback.message)
    callback_query_data = int(callback.data)

    if (await async_db_crud.tg_callback_query_log.select(f"True "
                                                         f"from dbo.tg_callback_query_log "
                                                         f"where chat_id = {user_tg_id}::BIGINT "
                                                         f"and message_id = {message_id}::BIGINT "
                                                         f"limit 1",
                                                         fetch_type='fetchone')) is not None:
        return

    ClassUser.user_id = user_id

    await bot.send_chat_action(chat_id=user_tg_id, action='typing')
    asyncio.create_task(user_management.delete_inline_keyboard_from_last_bot_message(user_tg_id))
    asyncio.create_task(async_db_crud.tg_callback_query_log.insert(f"({user_tg_id}, {message_id})"))

    user_status = await ClassUser.get_status(user_id)

    if user_status == 1:
        levels_kb, levels_dict = await user_management.get_levels_data()

        if callback_query_data in levels_dict.keys():
            await ClassUser.set_status(user_id, 2)
            level_id = callback_query_data
            await ClassUser.set_level_id(user_id, level_id)

            msg = await bot.send_message(user_tg_id,
                                         text=f'Вы выбрали уровень <b>{levels_dict[callback_query_data]}</b>',
                                         parse_mode='HTML')
            msg_copy = copy(msg)

            asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))

            await message_response(callback.message, old_messages_ignore=True)

    if user_status == 2:
        level_id = await ClassUser.get_level_id(user_id)
        lessons_kb, lessons_dict = await user_management.get_lessons_data(level_id)
        if callback_query_data in lessons_dict.keys():
            await ClassUser.set_status(user_id, 3)

            # IT-22 Add a message that the user has already started the lesson,
            # and we continue it from the same place where he left off
            lesson_id = await ClassUser.get_lesson_id(user_id)
            changing_lesson = False
            if lesson_id != callback_query_data:
                changing_lesson = True

            await ClassUser.set_lesson_id(user_id, callback_query_data)
            step_id = await user_management.lessons_current_step(user_id, callback_query_data)
            await ClassUser.set_step_id(user_id, step_id)

            msg = await bot.send_message(user_tg_id,
                                         text=f"Вы выбрали урок <b>{lessons_dict[callback_query_data]}</b>",
                                         parse_mode='HTML')
            msg_copy = copy(msg)

            asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))

            # IT-22
            connection_type = await ClassUser.get_connection_type(user_id)
            if changing_lesson and connection_type not in ('start', 'repeat_lesson'):
                await bot.send_message(user_tg_id,
                                       text='Вы уже начинали этот урок, мы запускаем его с того места, на котором вы остановились. '
                                            'Если хотите начать урок с начала или перейти сразу к итоговой тренировке, '
                                            'нажмите кнопку start_lesson_from_beginning',
                                       parse_mode='HTML')

            await message_response(callback.message, old_messages_ignore=True)

    if user_status == 3:
        lesson_id = await ClassUser.get_lesson_id(user_id)
        await user_management.is_start_lesson(user_id, lesson_id)

        step_id = await ClassUser.get_step_id(user_id)
        step_data_dict, step_kb, step_answers_dict = await user_management.get_step_data(step_id)
        answer_value = step_answers_dict[callback_query_data]

        connection_type = await ClassUser.get_connection_type(user_id)
        if callback_query_data in step_answers_dict.keys() \
                and (connection_type in ('start', 'repeat_lesson') or step_data_dict['type'] == 'choosing'):

            start_step_id = await user_management.lessons_first_step(lesson_id)
            # record = (await async_db_crud.routs_catalog.select(f"a.object_id, connection_type "
            #                                                    f"from dbo.routs_catalog a "
            #                                                    f"inner join dbo.steps s "
            #                                                    f"on a.actual = s.actual "
            #                                                    f"and a.object_id = s.id "
            #                                                    f"where a.entity_type = 'lessons' "
            #                                                    f"and a.entity_id = {lesson_id}::INTEGER "
            #                                                    f"and a.user_id is null "
            #                                                    f"and a.connection_type = 'optional' "
            #                                                    f"and a.parent_object_id = {start_step_id}::INTEGER "
            #                                                    f"and ('{answer_value}' = 'нет' and s.type = 'theory' "
            #                                                    f"or "
            #                                                    f"'{answer_value}' != 'нет' and s.type = 'final_training')"
            #                                                    f"and a.actual = True",
            #                                                    'fetchone'))
            if step_data_dict['type'] == 'choosing':
                next_step_id = python_object_tables.steps_dict[step_id]['next_step_data'][answer_value]
            else:
                next_step_id = python_object_tables.steps_dict[start_step_id]['next_step_data'][answer_value]

            next_step_data = [next_step_id, 'optional']
            await user_management.is_end_lesson(user_id, lesson_id, next_step_data, callback.message)
            await ClassUser.set_step_id(user_id, next_step_data[0])
            ClassUser.connection_type = next_step_data[1]

            await message_response(callback.message, old_messages_ignore=True, message_log_skip=False)

        if callback_query_data in step_answers_dict.keys() and step_data_dict['type'] == 'closed_question':
            if message_id == (await async_db_crud.tg_message_log.select(f"message_id "
                                                                        f"from dbo.tg_message_log "
                                                                        f"where chat_id = {user_tg_id}::BIGINT  "
                                                                        f"and is_bot = True "
                                                                        f"order by dadd desc "
                                                                        f"limit 1",
                                                                        fetch_type='fetchone'))['message_id']:

                if callback.message.text is not None:
                    if answer_value == "I'm not":
                        replacement = callback.message.text.replace(' …', f"<u>'m not</u>")
                    elif answer_value == "no":
                        replacement = callback.message.text.replace(' …', '')
                    else:
                        replacement = callback.message.text.replace('…', f"<u>{answer_value}</u>")

                    await bot.edit_message_text(chat_id=user_tg_id,
                                                message_id=message_id,
                                                text=replacement,
                                                reply_markup=None,
                                                parse_mode='HTML')
                elif callback.message.caption is not None:
                    if answer_value == "I'm not":
                        replacement = callback.message.caption.replace(' …', f"<u>'m not</u>")
                    else:
                        replacement = callback.message.caption.replace('…', f"<u>{answer_value}</u>")

                    await bot.edit_message_caption(chat_id=user_tg_id,
                                                   message_id=message_id,
                                                   caption=replacement,
                                                   reply_markup=None,
                                                   parse_mode='HTML')
                if answer_value == step_data_dict['answer_text']:
                    # correct answer
                    await user_management.set_user_progress_data(user_id, lesson_id, step_id, answer_value, True)
                    await ClassUser.set_step_id(user_id, 9)

                # IT-21
                elif step_data_dict['almost_correct'] and answer_value in list(step_data_dict['almost_correct'].keys()):
                    # almost correct answer given
                    await user_management.set_user_progress_data(user_id, lesson_id, step_id, answer_value, True)
                    await ClassUser.set_step_id(user_id, 323)

                else:
                    # wrong answer
                    await user_management.set_user_progress_data(user_id, lesson_id, step_id, answer_value, False)
                    await ClassUser.set_step_id(user_id, 116)
                ClassUser.connection_type = 'teacher_reaction'
                await message_response(callback.message, old_messages_ignore=True)

        if callback_query_data in step_answers_dict.keys() and step_data_dict['type'] == 'portioning':
            # record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
            #                                                   f"from dbo.routs_catalog "
            #                                                   f"where user_id is null "
            #                                                   f"and connection_type = 'mandatory' "
            #                                                   f"and parent_object_id = {step_id}::INTEGER "
            #                                                   f"and entity_type = 'lessons' "
            #                                                   f"and entity_id = {lesson_id}::INTEGER "
            #                                                   f"and actual = True "
            #                                                   f"order by dadd desc limit 1",
            #                                                   'fetchone')
            #
            # next_step_data = [record['object_id'], record['connection_type']]
            # if next_step_data is not None:
            #     await ClassUser.set_step_id(user_id, next_step_data[0])
            #     ClassUser.connection_type = next_step_data[1]
            #     await message_response(callback.message, old_messages_ignore=True)
            # if len(step_data_dict['next_step_data']) == 1:
            if isinstance(step_data_dict['next_step_data'], int):
                step_id = int(step_data_dict['next_step_data'])
                connection_type = 'mandatory' if isinstance(step_data_dict['next_step_data'], int) else 'optional'
                await ClassUser.set_step_id(user_id, step_id)
                ClassUser.connection_type = connection_type
                await message_response(callback.message, old_messages_ignore=True)

        if callback_query_data in step_answers_dict.keys() and step_data_dict['type'] == 'need_help':

            previous_question_id = (await async_db_crud.user_progress.select(f"object_id "
                                                                             f"from dbo.user_progress "
                                                                             f"where user_id = {user_id}::BIGINT "
                                                                             f"and entity_type = 'lessons' "
                                                                             f"and entity_id = {lesson_id}::INTEGER "
                                                                             f"and object_type = 'step' "
                                                                             f"and object_id not in (9, 116, 305, 323) "
                                                                             f"order by dadd desc limit 1",
                                                                             fetch_type='fetchone'))['object_id']

            if answer_value == 'нет':
                # previous_question_connection_type = \
                #     (await async_db_crud.routs_catalog.select(f"connection_type "
                #                                               f"from dbo.routs_catalog "
                #                                               f"where user_id is null "
                #                                               f"and connection_type = 'mandatory' "
                #                                               f"and object_id = {previous_question_id}::INTEGER "
                #                                               f"and entity_type = 'lessons' "
                #                                               f"and entity_id = {lesson_id}::INTEGER "
                #                                               f"and actual = True "
                #                                               f"order by dadd desc limit 1",
                #                                               fetch_type='fetchone'))['connection_type']

                await ClassUser.set_step_id(user_id, previous_question_id)
                ClassUser.connection_type = 'mandatory'
                await message_response(callback.message, old_messages_ignore=True)
                
            else:
                previous_step_text_with_answer = python_object_tables.steps_dict[previous_question_id]['step_text_with_answer']
                await bot.send_message(user_tg_id, text=previous_step_text_with_answer, reply_markup=None, parse_mode='HTML')
                error_count: int = (await user_management.get_error_effort_count(user_id, previous_question_id))
                
                if error_count > 0:
                    await async_db_crud.error_effort_count.update(f"err_count = 0 ",
                                                                  f"user_id = {user_id} and step_id = {previous_question_id}")

                # record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                #                                                   f"from dbo.routs_catalog "
                #                                                   f"where user_id is null "
                #                                                   f"and connection_type = 'mandatory' "
                #                                                   f"and parent_object_id = {previous_question_id}::INTEGER "
                #                                                   f"and entity_type = 'lessons' "
                #                                                   f"and entity_id = {lesson_id}::INTEGER "
                #                                                   f"and actual = True "
                #                                                   f"order by dadd desc limit 1",
                #                                                   'fetchone')

                # step_data_dict = python_object_tables.steps_dict[previous_question_id]

                next_step_data = await user_management.get_next_step_data(step_id=previous_question_id,
                                                                          lesson_id=lesson_id)
                # if len(step_data_dict['next_step_data']) == 1:
                #     step_id = list(step_data_dict['next_step_data'].keys())[0]
                #     connection_type = step_data_dict['next_step_data'][step_id]
                #     next_step_data = [step_id, connection_type]
                # else:
                #     record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                #                                                       f"from dbo.routs_catalog "
                #                                                       f"where user_id is null "
                #                                                       f"and connection_type = 'mandatory' "
                #                                                       f"and parent_object_id = {previous_question_id}::INTEGER "
                #                                                       f"and entity_type = 'lessons' "
                #                                                       f"and entity_id = {lesson_id}::INTEGER "
                #                                                       f"and actual = True "
                #                                                       f"order by dadd desc limit 1",
                #                                                       'fetchone')
                #
                #     if record is not None:
                #         next_step_data = [record['object_id'], record['connection_type']]
                #     else:
                #         next_step_data = []
        
                await user_management.is_end_lesson(user_id, lesson_id, next_step_data, callback.message)
                if next_step_data:
                    await ClassUser.set_step_id(user_id, next_step_data[0])
                    ClassUser.connection_type = next_step_data[1]
                    await message_response(callback.message, old_messages_ignore=True)

    return


@logger.catch()
@dp.message_handler()
async def message_response(message: types.Message,
                           old_messages_ignore=False,
                           message_log_skip=False):
    """
    if a message was received, this func is for action
    :param message:
    :param old_messages_ignore: this param equals True during recursive call of this func.
    after message from user processed once we don't need to do it again
    :param message_log_skip: if message from user received for the first time, we have to insert it to tg_message_log table
    :return:
    """
    user_tg_id = message.chat.id
    message_id = message.message_id
    if message.text is not None:
        message_text = message.text.replace("’", "'")
    elif message.caption is not None:
        message_text = message.caption.replace("’", "'")

    user_id = await user_management.set_user_id_from_tg(message)
    await bot.send_chat_action(chat_id=user_tg_id, action='typing')
    asyncio.create_task(user_management.delete_inline_keyboard_from_last_bot_message(user_tg_id))

    ClassUser.is_new_message = False
    if not message_log_skip and not message.from_user.is_bot:
        if (await async_db_crud.tg_message_log.select(f"True "
                                                      f"from dbo.tg_message_log "
                                                      f"where chat_id = {user_tg_id}::BIGINT "
                                                      f"and message_id = {message_id}::BIGINT "
                                                      f"and is_bot = False "
                                                      f"limit 1",
                                                      fetch_type='fetchone')) is None:
            ClassUser.is_new_message = True
            asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {message_id}, False, False)"))

    # get user_id
    ClassUser.user_id = user_id

    if (await async_db_crud.users.select(f"blocked "
                                         f"from dbo.users "
                                         f"where id = {user_id}::BIGINT "
                                         f"and actual = True "
                                         f"order by dadd desc "
                                         f"limit 1",
                                         fetch_type='fetchone'))['blocked']:
        await bot.send_message(user_tg_id,
                               text='Ой! Кажется, вы не внесли оплату&#129300',
                               parse_mode='HTML')
        return

    if not old_messages_ignore or ClassUser.is_new_message:
        if demojize(message_text) in ['/start', ':blue_book:levels', '\\xf0\\x9f\\x93\\x98levels']:
            if message_text == '/start':
                msg = await bot.send_message(user_tg_id,
                                             text=emojize(f'Вас приветствует <i>поли-бот</i>!'
                                                          f'\nгорячие кноки:'
                                                          f'\n:blue_book:levels — посмотреть доступные уровни знания английского'
                                                          f'\n:notebook_with_decorative_cover:lessons — посмотреть доступные уроки в рамках выбранного уровня знания английского'
                                                          f'\n:open_book:start_lesson_from_beginning — начать текущий урок с начала'),
                                             parse_mode='HTML',
                                             reply_markup=user_management.rkm
                                             )
                msg_copy = copy(msg)
                asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))

            await ClassUser.set_lesson_id(user_id, None)
            await ClassUser.set_status(user_id, 1)

        if demojize(message_text) in (':notebook_with_decorative_cover:lessons', '\\xf0\\x9f\\x93\\x94lessons'):
            if await ClassUser.get_level_id(user_id) is None:
                msg = await bot.send_message(user_tg_id,
                                             text='Сначала надо выбрать уровень знания английского',
                                             parse_mode='HTML')
                msg_copy = copy(msg)
                asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))
                await ClassUser.set_status(user_id, 1)
                message.text = ':blue_book:levels'
                await message_response(message)
                return
            else:
                await ClassUser.set_status(user_id, 2)

            await ClassUser.set_lesson_id(user_id, None)

        if demojize(message_text) in (':open_book:start_lesson_from_beginning', '\\xf0\\x9f\\x93\\x96start_lesson_from_beginning'):
            message_text = ':notebook_with_decorative_cover:lessons'
            lesson_id = await ClassUser.get_lesson_id(user_id)
            if lesson_id is None:
                msg = await bot.send_message(user_tg_id,
                                             text='Сначала надо выбрать урок',
                                             parse_mode='HTML')
                msg_copy = copy(msg)
                asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))
                await ClassUser.set_status(user_id, 2)
                await message_response(message)
                return
            else:
                is_start_lesson = await user_management.is_start_lesson(user_id, lesson_id)
                # if True, then user had started this lesson and yet not finished
                # if (await async_db_crud.user_progress.select(f"count(*) "
                #                                              f"from dbo.user_progress "
                #                                              f"where entity_type = 'lessons' "
                #                                              f"and entity_id = {lesson_id}::INTEGER "
                #                                              f"and object_type = 'step' "
                #                                              f"and actual = True",
                #                                              'fetchone'))['count'] != 0:
                if not is_start_lesson:
                    await async_db_crud.user_progress.update("actual = False",
                                                             f"user_id = {user_id}::BIGINT "
                                                             f"and entity_type = 'lessons' "
                                                             f"and entity_id = {lesson_id}::INTEGER "
                                                             f"and object_type = 'step' "
                                                             f"and actual = True")
                await ClassUser.set_status(user_id, 3)

    user_status = await ClassUser.get_status(user_id)

    # choosing level
    if user_status == 1:
        levels_kb, levels_dict = await user_management.get_levels_data()
        msg = await bot.send_message(user_tg_id,
                                     text='Выберите уровень знания английского',
                                     reply_markup=levels_kb,
                                     parse_mode='HTML')
        msg_copy = copy(msg)
        asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, True)"))

    # choosing lesson
    if user_status == 2:
        level_id = await ClassUser.get_level_id(user_id)
        lessons_kb, lessons_dict = await user_management.get_lessons_data(level_id)
        if len(lessons_kb['inline_keyboard']) > 0:
            msg = await bot.send_message(user_tg_id,
                                         text='Выберите урок',
                                         reply_markup=lessons_kb,
                                         parse_mode='HTML')
            msg_copy = copy(msg)
            asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, True)"))
        else:
            msg = await bot.send_message(user_tg_id,
                                         text='Простите, у нас пока нет уроков для вашего уровня английского&#128554',
                                         parse_mode='HTML')
            msg_copy = copy(msg)
            asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))
            await ClassUser.set_status(user_id, 1)
            await ClassUser.set_level_id(user_id, None)
            await message_response(message, old_messages_ignore=True)

    # learning a lesson
    if user_status == 3:
        lesson_id = await ClassUser.get_lesson_id(user_id)
        is_start_lesson = await user_management.is_start_lesson(user_id, lesson_id)

        step_id = await ClassUser.get_step_id(user_id)
        step_data_dict, step_kb, step_answers_dict = await user_management.get_step_data(step_id)

        # sending a message according to routs_catalog
        if not (ClassUser.is_new_message and step_data_dict['type'] == 'open_question')\
                and step_data_dict['type'] not in ('sticker', 'gif', 'set_of_additional_tasks'):
            if step_id not in (9, 116, 323):
                next_step_type = (await async_db_crud.routs_catalog.select(f"s.type "
                                                                           f"from dbo.routs_catalog rc "
                                                                           f"inner join dbo.steps s "
                                                                           f"on rc.object_id = s.id and s.actual = True "
                                                                           f"where rc.user_id is null "
                                                                           f"and rc.parent_object_id = {step_id}::INTEGER "
                                                                           f"and rc.entity_type = 'lessons' "
                                                                           f"and rc.entity_id = {lesson_id}::INTEGER "
                                                                           f"and rc.actual = True "
                                                                           f"order by rc.dadd desc limit 1 ",
                                                                           'fetchone'))

                if next_step_type is not None:
                    next_step_type = next_step_type['type']

                if step_data_dict['type'] == 'theory' and next_step_type in ('theory', 'portioning'):
                    step_kb = ReplyKeyboardRemove()
                elif step_data_dict['type'] == 'theory' and next_step_type not in ('theory', 'portioning'):
                    step_kb = user_management.rkm

            msg = await user_management.send_message_photo(user_tg_id,
                                                           text=step_data_dict['step_text'],
                                                           reply_markup=step_kb,
                                                           parse_mode='HTML',
                                                           step_id=step_id)

            # asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg}, True, {True if 'inline_keyboard' in step_kb.__str__() else False})"))
            asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, "
                                                                    f"{msg}, "
                                                                    f"True, "
                                                                    f"{True if hasattr(step_kb, 'inline_keyboard') else False})"
                                                                    )
                                )

        connection_type = await ClassUser.get_connection_type(user_id)
        if connection_type not in ('start', 'repeat_lesson'):

            if step_data_dict['type'] in ('theory', 'final_training'):
                if isinstance(step_data_dict['next_step_data'], int):
                    step_id = int(step_data_dict['next_step_data'])
                    # connection_type = step_data_dict['next_step_data'][step_id]
                    connection_type = 'mandatory'  # if isinstance(step_data_dict['next_step_data'], int) else 'optional'
                    next_step_data = [step_id, connection_type]
                elif step_data_dict['next_step_data'] is None:
                    next_step_data = None
                else:
                    record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                                                                      f"from dbo.routs_catalog "
                                                                      f"where user_id is null "
                                                                      f"and parent_object_id = {step_id}::INTEGER "
                                                                      f"and entity_type = 'lessons' "
                                                                      f"and entity_id = {lesson_id}::INTEGER "
                                                                      f"and actual = True "
                                                                      f"order by dadd desc limit 1",
                                                                      'fetchone')

                    if record is not None:
                        next_step_data = [record['object_id'], record['connection_type']]
                    else:
                        record = []
                        next_step_data = []

                await user_management.is_end_lesson(user_id, lesson_id, next_step_data, message)
                if next_step_data:
                    await ClassUser.set_step_id(user_id, next_step_data[0])
                    ClassUser.connection_type = next_step_data[1]

                    if step_data_dict['type'] == 'theory':
                        await sleep(1)

                    await message_response(message, old_messages_ignore=True)

            # if step_data_dict['type'] == 'gif':
            #     if isinstance(step_data_dict['next_step_data'], int):
            #         step_id = int(step_data_dict['next_step_data'])
            #         # connection_type = step_data_dict['next_step_data'][step_id]
            #         connection_type = 'mandatory'  # if isinstance(step_data_dict['next_step_data'], int) else 'optional'
            #         next_step_data = [step_id, connection_type]
            #     elif step_data_dict['next_step_data'] is None:
            #         next_step_data = None

            #     await user_management.is_end_lesson(user_id, lesson_id, next_step_data, message)


            if step_data_dict['type'] == 'open_question' and ClassUser.is_new_message:
                if message.from_user.is_bot:
                    msg = await bot.send_message(user_tg_id,
                                                 text=step_data_dict['step_text'],
                                                 parse_mode='HTML')
                    msg_copy = copy(msg)
                    asyncio.create_task(async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg_copy.message_id}, True, False)"))
                else:
                    answer_value = copy(message_text)
                    if answer_value.lower().replace('?', '').replace('!', '').replace('.', '') == (step_data_dict['answer_text'].lower().replace('?', '').replace('!', '').replace('.', '') if step_data_dict['answer_text'] is not None else ()) \
                    or answer_value.lower().replace('?', '').replace('!', '').replace('.', '') in (step_data_dict['answer_json'] if step_data_dict['answer_json'] is not None else ()):
                        # correct answer
                        await user_management.set_user_progress_data(user_id, lesson_id, step_id, answer_value, True)
                        await ClassUser.set_step_id(user_id, 9)

                    # IT-21
                    elif step_data_dict['almost_correct'] and answer_value.lower().replace('?', '').replace('!', '').replace('.', '') in list(step_data_dict['almost_correct'].keys()):
                        # almost correct
                        await user_management.set_user_progress_data(user_id, lesson_id, step_id, answer_value, True)
                        await ClassUser.set_step_id(user_id, 323)

                    else:
                        # wrong answer
                        await user_management.set_user_progress_data(user_id, lesson_id, step_id, answer_value, False)
                        await ClassUser.set_step_id(user_id, 116)
                    ClassUser.connection_type = 'teacher_reaction'
                await message_response(message, old_messages_ignore=True)

            if step_data_dict['type'] == 'teacher_reaction':
                previous_question_record = (await async_db_crud.user_progress.select(f"object_id, answer_text "
                                                                                     f"from dbo.user_progress "
                                                                                     f"where user_id = {user_id}::BIGINT "
                                                                                     f"and entity_type = 'lessons' "
                                                                                     f"and entity_id = {lesson_id}::INTEGER "
                                                                                     f"and object_type = 'step' "
                                                                                     f"and object_id not in (9, 116, 323) "
                                                                                     f"order by dadd desc limit 1",
                                                                                     fetch_type='fetchone'))

                previous_question_id = previous_question_record['object_id']
                previous_question_answer_text = previous_question_record['answer_text'].lower().replace('?', '').replace('!', '').replace('.', '')

                error_count = (await user_management.get_error_effort_count(user_id, previous_question_id))

                if step_id == 116:  # wrong answer was given
                    if error_count >= 2:
                        await ClassUser.set_step_id(user_id, 305)
                        ClassUser.connection_type = 'need_help'
                        #await async_db_crud.error_effort_count.update(f"err_count = 0 ",
                        #                                              f"user_id = {user_id} and step_id = {previous_question_id}")

                    else:
                        # previous_question_connection_type = \
                        #     (await async_db_crud.routs_catalog.select(f"connection_type "
                        #                                               f"from dbo.routs_catalog "
                        #                                               f"where user_id is null "
                        #                                               f"and connection_type = 'mandatory' "
                        #                                               f"and object_id = {previous_question_id}::INTEGER "
                        #                                               f"and entity_type = 'lessons' "
                        #                                               f"and entity_id = {lesson_id}::INTEGER "
                        #                                               f"and actual = True "
                        #                                               f"order by dadd desc limit 1",
                        #                                               fetch_type='fetchone'))['connection_type']

                        previous_question_connection_type = 'mandatory' if isinstance(python_object_tables.steps_dict[previous_question_id]['next_step_data'], int) else 'optional'

                        await ClassUser.set_step_id(user_id, previous_question_id)
                        ClassUser.connection_type = previous_question_connection_type

                    await async_db_crud.error_effort_count.update(f"err_count = {error_count + 1} ",
                                                                  f"user_id = {user_id} and step_id = {previous_question_id}")

                    await message_response(message, old_messages_ignore=True)

                elif step_id == 9:  # correct answer was given
                    #await user_management.go_to_next_step(error_count, user_id, lesson_id, previous_question_id)
                    #await message_response(message, old_messages_ignore=True)
                    
                    if error_count > 0:
                        await async_db_crud.error_effort_count.update(f"err_count = 0 ",
                                                                      f"user_id = {user_id} and step_id = {previous_question_id}")

                    # record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                    #                                                   f"from dbo.routs_catalog "
                    #                                                   f"where user_id is null "
                    #                                                   f"and connection_type = 'mandatory' "
                    #                                                   f"and parent_object_id = {previous_question_id}::INTEGER "
                    #                                                   f"and entity_type = 'lessons' "
                    #                                                   f"and entity_id = {lesson_id}::INTEGER "
                    #                                                   f"and actual = True "
                    #                                                   f"order by dadd desc limit 1",
                    #                                                   'fetchone')

                    # step_data_dict = python_object_tables.steps_dict[previous_question_id]

                    next_step_data = await user_management.get_next_step_data(step_id=previous_question_id,
                                                                              lesson_id=lesson_id)

                    # if len(step_data_dict['next_step_data']) == 1:
                    #     step_id = list(step_data_dict['next_step_data'].keys())[0]
                    #     connection_type = step_data_dict['next_step_data'][step_id]
                    #     next_step_data = [step_id, connection_type]
                    # else:
                    #     record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                    #                                                       f"from dbo.routs_catalog "
                    #                                                       f"where user_id is null "
                    #                                                       f"and connection_type = 'mandatory' "
                    #                                                       f"and parent_object_id = {previous_question_id}::INTEGER "
                    #                                                       f"and entity_type = 'lessons' "
                    #                                                       f"and entity_id = {lesson_id}::INTEGER "
                    #                                                       f"and actual = True "
                    #                                                       f"order by dadd desc limit 1",
                    #                                                       'fetchone')
                    #
                    #     if record is not None:
                    #         next_step_data = [record['object_id'], record['connection_type']]
                    #     else:
                    #         next_step_data = []

                    await user_management.is_end_lesson(user_id, lesson_id, next_step_data, message)
                    if next_step_data:
                        await ClassUser.set_step_id(user_id, next_step_data[0])
                        ClassUser.connection_type = next_step_data[1]
                        await message_response(message, old_messages_ignore=True)

                # IT-21
                elif step_id == 323:
                    step_data_dict = python_object_tables.steps_dict[previous_question_id]

                    await bot.send_message(user_tg_id,
                                           text=step_data_dict['almost_correct'][previous_question_answer_text][0],
                                           parse_mode='HTML')

                    next_step_data = await user_management.get_next_step_data(step_id=previous_question_id,
                                                                              lesson_id=lesson_id)
                    # if len(step_data_dict['next_step_data']) == 1:
                    #     step_id = list(step_data_dict['next_step_data'].keys())[0]
                    #     connection_type = step_data_dict['next_step_data'][step_id]
                    #     next_step_data = [step_id, connection_type]
                    # else:
                    #     record = await async_db_crud.routs_catalog.select(f"object_id, connection_type "
                    #                                                       f"from dbo.routs_catalog "
                    #                                                       f"where user_id is null "
                    #                                                       f"and connection_type = 'mandatory' "
                    #                                                       f"and parent_object_id = {previous_question_id}::INTEGER "
                    #                                                       f"and entity_type = 'lessons' "
                    #                                                       f"and entity_id = {lesson_id}::INTEGER "
                    #                                                       f"and actual = True "
                    #                                                       f"order by dadd desc limit 1",
                    #                                                       'fetchone')
                    #
                    #     if record is not None:
                    #         next_step_data = [record['object_id'], record['connection_type']]
                    #     else:
                    #         next_step_data = []

                    await user_management.is_end_lesson(user_id, lesson_id, next_step_data, message)
                    if next_step_data:
                        await ClassUser.set_step_id(user_id, next_step_data[0])
                        ClassUser.connection_type = next_step_data[1]
                        await message_response(message, old_messages_ignore=True)

            # IT-23
            if step_data_dict['type'] in ('sticker', 'gif'):

                # file_id = (await async_db_crud.stickergifs.select("s.file_id "
                #                                                    "from dbo.tag_stickersgifs ts "
                #                                                    "inner join dbo.stickersgifs s "
                #                                                    "on ts.id = s.tag_stickersgif_id "
                #                                                    "and ts.actual = true "
                #                                                    "and s.actual = true "
                #                                                    f"where ts.name = '{step_data_dict['step_text']}'::TEXT "
                #                                                    f"and s.type = '{step_data_dict['type']}'::TEXT "
                #                                                    "order by random() "
                #                                                    "limit 1",
                #                                                    'fetchone'))['file_id']

                file_id = random.choice(python_object_tables.sticker_gif_dict[(step_data_dict['step_text'], step_data_dict['type'])])

                msg = await bot.send_sticker(user_tg_id,
                                             sticker=file_id)

                await async_db_crud.tg_message_log.insert(f"({user_tg_id}, {msg.message_id}, True, False)")

                if isinstance(step_data_dict['next_step_data'], int):
                    step_id = int(step_data_dict['next_step_data'])
                    connection_type = 'mandatory' if isinstance(step_data_dict['next_step_data'], int) else 'optional'
                    await ClassUser.set_step_id(user_id, step_id)
                    ClassUser.connection_type = connection_type
                    next_step_data = [step_id, connection_type]
                    await message_response(message, old_messages_ignore=True)
                elif step_data_dict['next_step_data'] is None:
                    next_step_data = None

                await user_management.is_end_lesson(user_id, lesson_id, next_step_data, message)


            # IT-25
            if step_data_dict['type'] == 'set_of_additional_tasks':
                set_conditions = python_object_tables.steps_dict[step_id]['set_conditions']

                if set_conditions['set_condition'] == '% wrong answers':
                    set_start_id = set_conditions['set_start_id']


                    # validation_exercises_start_id -- id of a row in user_progress, when user last time started this set
                    validation_exercises_start_id = (await async_db_crud.user_progress.select("up.id "
                                                                                              "from dbo.user_progress up "
                                                                                              "inner join dbo.routs_catalog rc "
                                                                                              "on up.object_id = rc.object_id "
                                                                                              "and up.entity_id = rc.entity_id "
                                                                                              "and rc.object_type = 'step' "
                                                                                              "and rc.entity_type = 'lessons' "
                                                                                              f"and up.object_id = {set_start_id} "
                                                                                              f"where up.user_id = {user_id} "
                                                                                              f"and up.entity_id = {lesson_id} "
                                                                                              "order by up.dadd desc "
                                                                                              "limit 1",
                                                                                              fetch_type='fetchone'))['id']

                    logger.info(f"validation_exercises_start_id {validation_exercises_start_id}")

                    # users_result -- how many wrong/correct answers were given by user on our question in this set
                    users_result = json.loads(
                        (await async_db_crud.user_progress.select("json_object_agg(correct, coalesce(cnt, 0)) joa "
                                                                  "from ( "
                                                                  "select a.correct, b.cnt "
                                                                  "    from (values "
                                                                  "          ('wrong'), "
                                                                  "          ('correct') "
                                                                  "         )a (correct) "
                                                                  "left join "
                                                                  "    ( "
                                                                  "    select case correct "
                                                                  "                when false then 'wrong' "
                                                                  "                when true then 'correct' "
                                                                  "            end correct, "
                                                                  "           count(*) cnt "
                                                                  "        from ( "
                                                                  "            select up.object_id, up.correct, row_number() over (partition by up.object_id order by up.dadd) rn "
                                                                  "                from dbo.user_progress up "
                                                                  "            inner join dbo.steps s "
                                                                  "            on up.object_id = s.id "
                                                                  "            and up.object_type = 'step' "
                                                                  "            and up.entity_id = s.lesson_id "
                                                                  "            and up.entity_type = 'lessons' "
                                                                  "            and s.actual = true "
                                                                  "            and s.type in ('open_question', 'closed_question') "
                                                                  "            and up.correct is not null "
                                                                  f"           where up.user_id = {user_id} "
                                                                  f"           and up.entity_id = {lesson_id} "
                                                                  f"           and up.id >= {validation_exercises_start_id} "
                                                                  "            order by up.dadd desc "
                                                                  "              )t "
                                                                  "     where rn = 1 "
                                                                  "     group by correct "
                                                                  "    )b "
                                                                  "    on a.correct = b.correct "
                                                                  ")t", 
                                                                    fetch_type='fetchone'))['joa'] 
                        )    

                    logger.info(f"users_result {users_result}")

                    percentage_of_wrong_answers = (float(users_result['wrong'])/(float(users_result['wrong'])+float(users_result['correct'])))

                    logger.info(f"percentage_of_wrong_answers {percentage_of_wrong_answers}")

                    connection_type = 'optional'
                    if percentage_of_wrong_answers*100 >= set_conditions['condition_threshold']:
                        next_step = set_conditions['next_step']['if_condition_true']
                    else:
                        next_step = set_conditions['next_step']['if_condition_false']

                    await ClassUser.set_step_id(user_id, next_step)
                    ClassUser.connection_type = connection_type
                    await message_response(message, old_messages_ignore=True)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
