import httplib2
import datetime
import config
import asyncio
import asyncpg

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials
from loguru import logger

logger.add("debug_logs/debug_google_sheets_export.log",
           format="{time} {level} {message}",
           level="DEBUG",
           rotation="10 KB",
           compression="zip")

credential_file = config.credential_file
spreadsheet_id = config.spreadsheet_id

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    credential_file,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive'])

httpAuth = credentials.authorize(httplib2.Http())
service = discovery.build('sheets', 'v4', http=httpAuth)
sheet = service.spreadsheets()


@logger.catch()
def update_values(spreadsheet_id, range_name, value_input_option, values, sheet):
    """
    use this func to update data in google sheets
    :param spreadsheet_id:
    :param range_name:
    :param value_input_option:
    :param values:
    :param sheet:
    :return:
    """
    try:

        body = {
            'values': values
        }

        result = sheet.values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption=value_input_option, body=body).execute()

        return result
    except HttpError as error:

        return error


def time_mark(list_name: str):
    update_values(spreadsheet_id,
                  range_name=f"{list_name}!C1",
                  value_input_option="USER_ENTERED",
                  values=[
                              [str(datetime.datetime.utcnow().isoformat(timespec='minutes'))]
                          ],
                  sheet=sheet)


def is_correct_answer(text: str):
    if text == 'True':
        return 'Да'
    elif text == 'False':
        return 'Нет'
    else:
        return None


@logger.catch()
async def main():
    conn = await asyncpg.connect(dsn=config.dsn)

    # Пользователи
    time_mark('Пользователи')

    selection = (await conn.fetch(f"select ut.user_id, ut.id, ut.dadd, ut.first_name, ut.last_name, ut.username, ut.is_premium, u.blocked "
                                        "from dbo.users_tg ut "
                                    "inner join dbo.users u "
                                    "on ut.user_id = u.id "
                                    "and ut.actual = true "
                                    "and u.actual = true")
                  )

    batch_update = [
                        [str(s['user_id']),
                         str(s['id']),
                         str(s['dadd'].isoformat(timespec='minutes')),
                         str(s['first_name']),
                         str(s['last_name']),
                         str(s['username']),
                         'Да' if str(s['is_premium']) == 'True' else 'Нет',
                         'Да' if str(s['blocked']) == 'True' else 'Нет'
                        ] for s in selection
                    ]

    if len(batch_update) > 0:
        update_values(spreadsheet_id,
                      range_name=f"Пользователи!A{4}:H{4+len(batch_update)}",
                      value_input_option="USER_ENTERED",
                      values=batch_update,
                      sheet=sheet)

    selection = batch_update = None

    # Количество ошибок по каждому тесту
    time_mark('Количество ошибок по каждому тесту')

    selection = (await conn.fetch(
                                   "select ut.first_name, ut.last_name, ut.username, l.name lesson_name, s.step_text, up.cnt "
                                   "    from( "
                                   "        select user_id, entity_id as lesson_id, object_id as step_id, count(*) cnt "
                                   "            from dbo.user_progress "
                                   "        where id > 6501 "
                                   "        and entity_type = 'lessons' "
                                   "        and object_type = 'step' "
                                   "        and correct = false "
                                   "        group by user_id, entity_id, object_id "
                                   "        )up "
                                   "inner join dbo.users_tg ut "
                                   "on up.user_id = ut.user_id and ut.actual = true "
                                   "inner join dbo.lessons l "
                                   "on up.lesson_id = l.id and l.actual = true "
                                   "inner join dbo.steps s "
                                   "on up.step_id = s.id and s.actual = true "
                                   "order by ut.username, l.id, s.id"
                                   )
                 )

    batch_update = [
                        [str(s['first_name']),
                         str(s['last_name']),
                         str(s['username']),
                         str(s['lesson_name']),
                         str(s['step_text']).replace('&#128577;', '').replace('&#128515;', '').replace('<i>', '').replace('</i>', '').replace('<b>', '').replace('</b>', ''),
                         str(s['cnt'])
                        ] for s in selection
                    ]

    if len(batch_update) > 0:
        update_values(spreadsheet_id,
                      range_name=f"Количество ошибок по каждому тесту!A{4}:H{4+len(batch_update)}",
                      value_input_option="USER_ENTERED",
                      values=batch_update,
                      sheet=sheet)

    selection = batch_update = None

    # Прогресс пользователей
    time_mark('Прогресс пользователей')

    selection = (await conn.fetch(
                                  "select up.dadd, ut.username, l.name lesson_name, s.type, s.step_text, up.answer_text, up.correct "
                                  "    from dbo.user_progress up "
                                  "inner join dbo.users_tg ut "
                                  "on up.user_id = ut.user_id and ut.actual = true "
                                  "inner join dbo.lessons l "
                                  "on up.entity_id = l.id and l.actual = true "
                                  "inner join dbo.steps s "
                                  "on up.object_id = s.id and s.actual = true "
                                  "where up.id > 6501 "
                                  "and up.entity_type = 'lessons' "
                                  "and up.object_type = 'step' "
                                  "order by ut.id, up.dadd desc"
                                )
                 )

    batch_update = [
                        [
                            s['dadd'].isoformat(timespec='minutes'),
                            str(s['username']),
                            str(s['lesson_name']),
                            str(s['type']),
                            str(s['step_text']).replace('&#128577;', '').replace('&#128515;', '').replace('<i>', '').replace('</i>', '').replace('<b>', '').replace('</b>', ''),
                            str(s['answer_text']) if str(s['answer_text']) != 'None' else None,
                            is_correct_answer(str(s['correct']))
                        ] for s in selection]

    if len(batch_update) > 0:
        update_values(spreadsheet_id,
                      range_name=f"Прогресс пользователей!A{4}:G{4+len(batch_update)}",
                      value_input_option="USER_ENTERED",
                      values=batch_update,
                      sheet=sheet)

    selection = batch_update = None

    await conn.close()


asyncio.get_event_loop().run_until_complete(main())

while True:
    if datetime.datetime.utcnow().strftime("%H:%M:%S") == '00:00:00':
        asyncio.get_event_loop().run_until_complete(main())

