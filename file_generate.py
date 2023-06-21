import asyncio
import datetime
import config
import asyncpg
import json
import codecs

from loguru import logger

logger.add("debug_logs/debug_file_generate.log",
           format="{time} {level} {message}",
           level="DEBUG",
           rotation="10 KB",
           compression="zip")


@logger.catch()
async def main():
    # Establish a connection to an existing database named "test"
    # as a "postgres" user.
    conn = await asyncpg.connect(dsn='postgres://postgres:YgHfxZ(q@localhost:5432/english_buddy_bot_db')# (dsn=config.dsn)

    levels = await conn.fetch('select name, id ' 
                              'from dbo.levels '
                              'where actual = true '
                              'order by row_order')

    levels_list = []
    for level in levels:
        levels_list.append((level['name'], level['id']))

    lessons_dict = {}
    for l in levels_list:
        level_id = l[1]

        lessons = await conn.fetch('select name, id '
                                   'from dbo.lessons '
                                   f"where level_id = {level_id}::INTEGER "
                                   f"and actual = true "
                                   f"order by id")

        if lessons:
            lessons_dict[level_id] = []
            for l in lessons:
                lessons_dict[level_id].append((l['name'], l['id']))

    lessons_start_and_repeat_step_id_dict = {}
    lessons_start_and_repeat_step_id = await conn.fetch("select s.lesson_id, "
                                                                "json_object_agg(rc.connection_type, s.id) joa "
                                                        "from dbo.steps s "
                                                        "inner join dbo.routs_catalog rc "
                                                        "on s.id = rc.object_id "
                                                        "and s.actual = true "
                                                        "and rc.actual = true "
                                                        "and s.lesson_id = rc.entity_id "
                                                        "where rc.connection_type in ('start', 'repeat_lesson') "
                                                        "group by s.lesson_id")

    for l in lessons_start_and_repeat_step_id:
        lessons_start_and_repeat_step_id_dict[l['lesson_id']] = json.loads(l['joa'])

    files_dict = {}
    files = await conn.fetch('select step_id, '
                             "concat(python_package_name,'/',file_name) as ja "
                             'from dbo.files '
                             'where actual = true')

    for f in files:
        if f['step_id'] not in files_dict:
            files_dict[f['step_id']] = [f['ja']]
        else:
            files_dict[f['step_id']].append(f['ja'])

    steps_dict = {}
    steps = await conn.fetch("select s.id, "
                             "       s.type, "
                             "       s.step_text, "
                             "       s.answer_text, "
                             "       s.answer_json, "
                             "       s.step_text_with_answer, "
                             "       rc.cnt, "
                             "       rc.next_step_data, "
                             "       s.almost_correct, "
                             "       (select case when json_data ->> 'set_conditions' is not null then json_data end "
                             "            from dbo.routs_catalog rc "
                             "            where rc.actual = true "
                             "            and rc.entity_type = 'lessons' "
                             "            and rc.entity_id = s.lesson_id "
                             "            and rc.object_type = 'step' "
                             "            and rc.object_id = s.id "
                             "       limit 1) set_conditions "
                             "    from dbo.steps s "
                             "left join ( "
                             "            select entity_id, "
                             "            parent_object_id, "
                             "            count(object_id) cnt, "
                             "            json_object_agg(coalesce((json_data->> 'choosing_text')::varchar(100), connection_type), object_id) next_step_data "
                             "                from dbo.routs_catalog "
                             "            where user_id is null "
                             "            and entity_type = 'lessons' "
                             "            and object_type = 'step' "
                             "            and actual = True "
                             "            group by entity_id, parent_object_id "
                             "    )rc "
                             "on s.id = rc.parent_object_id and (s.lesson_id = rc.entity_id or s.lesson_id is null) "
                             "    where s.actual = true"
                             )

    for s in steps:

        if s['cnt'] == 1:
            next_step_data = int(list(json.loads(s['next_step_data']).values())[0])
        elif s['cnt'] is not None and s['cnt'] > 1 and s['next_step_data'] is not None:
            next_step_data = json.loads(s['next_step_data'])
        else:
            next_step_data = None

        steps_dict[s['id']] = {
                               'type': s['type'],
                               'step_text': str(s['step_text']).replace("\\n", "\n") if s['step_text'] is not None else None,
                               'answer_text': s['answer_text'],
                               'answer_json': (json.loads(s['answer_json']) if s['answer_json'] is not None else None),
                               'step_text_with_answer': str(s['step_text_with_answer']).replace("\\n", "\n") if s['step_text_with_answer'] is not None else None,
                               'next_step_data': (next_step_data
                                                  # json.loads(s['next_step_data']) if s['next_step_data'] is not None else None
                                                    ),
                               'almost_correct': (json.loads(s['almost_correct']) if s['almost_correct'] is not None else None),
                               'set_conditions': (json.loads(s['set_conditions'])['set_conditions'] if s['set_conditions'] is not None else None)
                               }

        next_step_data = None

    sticker_gif_list = await conn.fetch("select ts.name, s.type, s.file_id "
                                        "    from dbo.stickersgifs s "
                                        "inner join dbo.tag_stickersgifs ts on ts.id = s.tag_stickersgif_id "
                                        "and s.actual = true and ts.actual = true")

    sticker_gif_dict = {}
    for row in sticker_gif_list:
        if (row['name'], row['type']) not in sticker_gif_dict:
            sticker_gif_dict[row['name'], row['type']] = [row['file_id']]
        else:
            sticker_gif_dict[row['name'], row['type']].append(row['file_id'])

    await conn.close()

    with codecs.open("python_object_tables.py", "w+", "utf-8") as file:
        file.write(f"levels_list = {levels_list}\n")
        file.write(f"lessons_dict = {str(lessons_dict)}\n")
        file.write(f"lessons_start_and_repeat_step_id_dict = {str(lessons_start_and_repeat_step_id_dict)}\n")
        file.write(f"files_dict = {str(files_dict)}\n")
        file.write(f"steps_dict = {str(steps_dict)}\n")
        file.write(f"sticker_gif_dict = {str(sticker_gif_dict)}\n")
        file.write(f"time_mark = '{datetime.datetime.now()}'\n")


asyncio.get_event_loop().run_until_complete(main())

# import python_object_tables
#
# print(python_object_tables.levels_list)
# print(python_object_tables.lessons_dict)
# print(python_object_tables.files_dict)
# print(python_object_tables.steps_dict)


