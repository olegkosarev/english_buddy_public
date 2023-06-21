import asyncio

import asyncpg
import config
from loguru import logger

logger.add("debug_logs/debug_db.log",
           format="{time} {level} {message}",
           level="DEBUG",
           rotation="50 KB",
           compression="zip")


class DbConnect:
    def __init__(self, pool, db_name, schema_name, table_name, columns,
                 dsn=config.dsn,
                 host=config.host,
                 user=config.user,
                 password=config.password,
                 port=config.port):
        self.pool = pool
        self.db_name = db_name
        self.schema_name = schema_name
        self.table_name = table_name
        self.dsn = dsn
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.columns = columns
        self.config = {
                'dsn': self.dsn # ,
                # 'host': self.host,
                # 'port': self.port,
                # 'database': self.db_name,
                # 'user': self.user,
                # 'password': self.password
                       }

    @logger.catch()
    async def select(self, query=None, fetch_type='fetchall'):
        if query is None:
            query = f'* from {self.db_name}.{self.schema_name}.{self.table_name}'

        async with self.pool.acquire() as conn:
            if fetch_type == 'fetchall':
                selection = await conn.fetch(f'select {query}')
            else:
                selection = await conn.fetchrow(f'select {query}')
        return selection

    @logger.catch()
    async def insert(self, values: str):
        async with self.pool.acquire() as conn:
            insert_query = f'insert into {self.db_name}.{self.schema_name}.{self.table_name} {self.columns} ' \
                           f'values {values}'
            await conn.execute(insert_query)

    @logger.catch()
    async def update(self, set_condition: str, where_condition: str):
        async with self.pool.acquire() as conn:
            update_query = f'update {self.db_name}.{self.schema_name}.{self.table_name} ' \
                           f'set {set_condition} ' \
                           f'where {where_condition}'
            await conn.execute(update_query)

    @logger.catch()
    async def delete(self, where_condition: str):
        async with self.pool.acquire() as conn:
            delete_query = f'delete from {self.db_name}.{self.schema_name}.{self.table_name} ' \
                           f'where {where_condition}'
            await conn.execute(delete_query)

    @logger.catch()
    async def check_id(self, id):
        async with self.pool.acquire() as conn:
            selection = await conn.fetchrow(f'select exists(select * from {self.schema_name}.{self.table_name} '
                                            f'where id ={id}::BIGINT and actual = True)')
            selection = selection[0]
        return selection


class DbConnectAdvanced(DbConnect):
    def __init__(self, pool, db_name, schema_name, table_name, columns, dsn=config.dsn, host=config.host,
                 user=config.user, password=config.password, port=config.port):
        super().__init__(pool, db_name, schema_name, table_name, columns, dsn, host, user, password, port)

    @logger.catch()
    async def special_update(self, answer_text, correct, where_condition: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(f"update {self.db_name}.{self.schema_name}.{self.table_name} "
                               f"set answer_text = $1, correct = $2 "
                               f"where {where_condition}",
                               answer_text, correct)


pool = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(dsn=config.dsn))


accesses = DbConnect(pool, config.db_name, 'dbo', 'accesses', '(name)')
files = DbConnect(pool, config.db_name, 'dbo', 'files', '(step_id, python_package_name, file_name)')
hierarchy = DbConnect(pool, config.db_name, 'dbo', 'hierarchy', '(layer, object_id, hierarchy_lvl)')
lesson_groups = DbConnect(pool, config.db_name, 'dbo', 'lesson_groups', '(level_id, eng_name, ru_name, row_order)')
lessons = DbConnect(pool, config.db_name, 'dbo', 'lessons', '(lesson_group_id, level_id, name)')
levels = DbConnect(pool, config.db_name, 'dbo', 'levels', '(name, row_order)')
role_accesses = DbConnect(pool, config.db_name, 'dbo', 'role_accesses', '(role_id, access_id)')
roles = DbConnect(pool, config.db_name, 'dbo', 'roles', '(name)')
routs_catalog = DbConnect(pool, config.db_name, 'dbo', 'routs_catalog', '(user_id, entity_type, entity_id, object_type, object_id, parent_object_id, connection_type)')
steps = DbConnect(pool, config.db_name, 'dbo', 'steps', '(lesson_id, type, step_text, answer_text, answer_json, step_text_with_answer)')
stickergifs = DbConnect(pool, config.db_name, 'dbo', 'stickergifs', '(type, link, tag_stickergif_id)')
tag_stickergifs = DbConnect(pool, config.db_name, 'dbo', 'tag_stickergifs', '(name)')
user_roles = DbConnect(pool, config.db_name, 'dbo', 'user_roles', '(user_id, role_id)')
users = DbConnect(pool, config.db_name, 'dbo', 'users', '(id, first_name, last_name)')
users_site = DbConnect(pool, config.db_name, 'dbo', 'users_site', '(first_name, last_name, user_id, password, mail)')
users_tg = DbConnect(pool, config.db_name, 'dbo', 'users_tg', '(id, first_name, last_name, user_id, username, is_premium)')
users_status = DbConnect(pool, config.db_name, 'dbo', 'users_status', '(user_id, status_id)')
statuses = DbConnect(pool, config.db_name, 'dbo', 'statuses', '(name)')
user_actual_level = DbConnect(pool, config.db_name, 'dbo', 'user_actual_level', '(user_id, level_id)')
user_actual_level_lesson = DbConnect(pool, config.db_name, 'dbo', 'user_actual_level_lesson', '(user_id, level_id, lesson_id)')
tg_message_log = DbConnect(pool, config.db_name, 'dbo', 'tg_message_log', '(chat_id, message_id, is_bot, has_inline_keyboard)')
tg_callback_query_log = DbConnect(pool, config.db_name, 'dbo', 'tg_callback_query_log', '(chat_id, message_id)')
user_finished_lessons = DbConnect(pool, config.db_name, 'dbo', 'user_finished_lessons', '(user_id, lesson_id)')
error_effort_count = DbConnect(pool, config.db_name, 'dbo', 'error_effort_count', '(user_id, step_id, err_count)')
user_progress = DbConnectAdvanced(pool, config.db_name, 'dbo', 'user_progress', '(user_id, entity_type, entity_id, object_type, object_id, answer_text, correct)')
