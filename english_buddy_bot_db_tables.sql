create table users_site
(
    id         integer,
    dadd       timestamp default now(),
    actual     boolean   default true,
    first_name varchar(100),
    last_name  varchar(100),
    user_id    integer,
    password   varchar(100),
    mail       varchar(100)
);

alter table users_site
    owner to postgres;

create index actual_user_site
    on users_site (id, actual);

grant insert, select, update on users_site to tg_user;

create table roles
(
    id     integer generated by default as identity,
    dadd   timestamp default now(),
    actual boolean   default true,
    name   varchar(100)
);

alter table roles
    owner to postgres;

create index actual_role
    on roles (id, actual);

grant insert, select, update on roles to tg_user;

create table user_roles
(
    id      integer generated by default as identity,
    dadd    timestamp default now(),
    actual  boolean   default true,
    user_id integer,
    role_id integer
);

alter table user_roles
    owner to postgres;

create index actual_user_role
    on user_roles (id, actual);

create index user_roles_actual_user_id
    on user_roles (user_id, actual);

create index actual_role_id
    on user_roles (role_id, actual);

grant insert, select, update on user_roles to tg_user;

create table accesses
(
    id      bigint generated by default as identity,
    dadd    timestamp default now(),
    actual  boolean   default true,
    name    varchar(100),
    blocked boolean   default false
);

alter table accesses
    owner to postgres;

create index accesses_actual_role
    on accesses (id, actual, blocked);

grant insert, select, update on accesses to tg_user;

create table role_accesses
(
    id        integer generated by default as identity,
    dadd      timestamp default now(),
    actual    boolean   default true,
    role_id   integer,
    access_id integer
);

alter table role_accesses
    owner to postgres;

create index role_accesses_actual_user_role
    on role_accesses (id, actual);

create index role_accesses_actual_role_id
    on role_accesses (role_id, actual);

create index actual_access_id
    on role_accesses (access_id, actual);

grant insert, select, update on role_accesses to tg_user;

create table hierarchy
(
    id            integer generated by default as identity,
    dadd          timestamp default now(),
    actual        boolean   default true,
    layer         varchar(100),
    object_id     bigint,
    hierarchy_lvl integer
);

alter table hierarchy
    owner to postgres;

create index actual_hierarchy
    on hierarchy (id, actual);

create index actual_layer_object_id
    on hierarchy (layer, object_id, actual);

grant insert, select, update on hierarchy to tg_user;

create table files
(
    id          integer generated by default as identity,
    dadd        timestamp default now(),
    actual      boolean   default true,
    step_id     integer,
    link        varchar(200),
    name        varchar(100),
    data_type   varchar(100),
    mime        varchar(100),
    description text
);

alter table files
    owner to postgres;

create index files_actual_step
    on files (id, actual);

create index actual_step_id
    on files (step_id, actual);

grant insert, select, update on files to tg_user;

create table stickersgifs
(
    id                 integer generated by default as identity,
    dadd               timestamp default now(),
    actual             boolean   default true,
    type               varchar(100),
    link               varchar(200),
    tag_stickersgif_id integer
);

alter table stickersgifs
    owner to postgres;

create index stickersgifs_actual_step
    on stickersgifs (id, actual);

create index actual_stickersgif_tag_id
    on stickersgifs (tag_stickersgif_id, actual);

grant insert, select, update on stickersgifs to tg_user;

create table tag_stickersgifs
(
    id     integer generated by default as identity,
    dadd   timestamp default now(),
    actual boolean   default true,
    name   varchar(100)
);

alter table tag_stickersgifs
    owner to postgres;

create index actual_tag_stickersgifs
    on tag_stickersgifs (id, actual);

grant insert, select, update on tag_stickersgifs to tg_user;

create table user_progress
(
    id          bigint generated by default as identity,
    dadd        timestamp default now(),
    actual      boolean   default true,
    user_id     integer,
    entity_type varchar(100),
    entity_id   integer,
    object_type varchar(100),
    object_id   bigint,
    answer_text text,
    correct     boolean
);

alter table user_progress
    owner to postgres;

grant insert, select, update on user_progress to tg_user;

create table lessons
(
    id              integer generated by default as identity,
    dadd            timestamp default now(),
    actual          boolean   default true,
    lesson_group_id integer,
    level_id        integer,
    name            varchar(100)
);

alter table lessons
    owner to postgres;

create index actual_lesson
    on lessons (id, actual);

create index actual_lesson_group_id
    on lessons (lesson_group_id, actual);

grant insert, select, update on lessons to tg_user;

create table levels
(
    id        integer generated by default as identity,
    dadd      timestamp default now(),
    actual    boolean   default true,
    name      varchar(100),
    row_order integer
);

alter table levels
    owner to postgres;

create index actual_level
    on levels (id, actual);

grant insert, select, update on levels to tg_user;

create table lesson_groups
(
    id        integer generated by default as identity,
    dadd      timestamp default now(),
    actual    boolean   default true,
    level_id  integer,
    eng_name  varchar(200),
    ru_name   varchar(200),
    row_order integer
);

alter table lesson_groups
    owner to postgres;

create index actual_lesson_group
    on lesson_groups (id, actual);

create index actual_level_id
    on lesson_groups (level_id, actual);

grant insert, select, update on lesson_groups to tg_user;

create table users
(
    id         integer generated by default as identity,
    dadd       timestamp default now(),
    actual     boolean   default true,
    first_name varchar(100),
    last_name  varchar(100),
    blocked    boolean   default false
);

alter table users
    owner to postgres;

create index actual_user
    on users (id, actual, blocked);

grant insert, select, update on users to tg_user;

create table users_tg
(
    id         bigint,
    dadd       timestamp default now(),
    actual     boolean   default true,
    first_name varchar(100),
    last_name  varchar(100),
    user_id    integer,
    username   varchar(100),
    is_premium boolean
);

alter table users_tg
    owner to postgres;

create index actual_user_id
    on users_tg (user_id, actual);

create index actual_user_tg
    on users_tg (id, actual);

grant insert, select, update on users_tg to tg_user;

create table statuses
(
    id     integer generated by default as identity,
    dadd   timestamp default now(),
    actual boolean   default true,
    name   varchar(100)
);

alter table statuses
    owner to postgres;

create index actual_statuses
    on statuses (id, actual);

grant insert, select, update on statuses to tg_user;

create table users_status
(
    id        integer generated by default as identity,
    dadd      timestamp default now(),
    actual    boolean   default true,
    user_id   integer,
    status_id integer
);

alter table users_status
    owner to postgres;

create index actual_users_id
    on users_status (actual, user_id);

create index actual_status_id
    on users_status (actual, status_id);

grant insert, select, update on users_status to tg_user;

create table user_actual_level
(
    id       integer generated by default as identity,
    dadd     timestamp default now(),
    actual   boolean   default true,
    user_id  integer,
    level_id integer
);

alter table user_actual_level
    owner to postgres;

create index users_actual_level
    on user_actual_level (actual, user_id, level_id);

grant insert, select, update on user_actual_level to tg_user;

create table user_actual_level_lesson
(
    id        integer generated by default as identity,
    dadd      timestamp default now(),
    actual    boolean   default true,
    user_id   integer,
    level_id  integer,
    lesson_id integer
);

alter table user_actual_level_lesson
    owner to postgres;

create index actual_users_level_lesson
    on user_actual_level_lesson (actual, user_id, level_id, lesson_id);

grant insert, select, update on user_actual_level_lesson to tg_user;

create table steps_
(
    dadd                  timestamp,
    actual                boolean,
    lesson_id             integer,
    type                  varchar(100),
    step_text             text,
    answer_text           text,
    answer_json           json,
    step_text_with_answer text
);

alter table steps_
    owner to postgres;

grant insert, select, update on steps_ to tg_user;

create table steps
(
    id                    integer generated by default as identity,
    dadd                  timestamp default now(),
    actual                boolean   default true,
    lesson_id             integer,
    type                  varchar(100),
    step_text             text,
    answer_text           text,
    answer_json           json,
    step_text_with_answer text
);

alter table steps
    owner to postgres;

create index actual_step
    on steps (id, actual);

create index actual_lesson_id
    on steps (lesson_id, actual);

grant insert, select, update on steps to tg_user;

create table routs_catalog_
(
    object_id        integer,
    parent_object_id integer,
    type             varchar(100),
    connection_type  text
);

alter table routs_catalog_
    owner to postgres;

grant insert, select, update on routs_catalog_ to tg_user;

create table routs_catalog
(
    id               integer generated by default as identity,
    dadd             timestamp default now(),
    actual           boolean   default true,
    user_id          integer,
    entity_type      varchar(100),
    entity_id        integer,
    object_type      varchar(100),
    object_id        integer,
    parent_object_id integer,
    connection_type  varchar(100)
);

alter table routs_catalog
    owner to postgres;

create index actual_route
    on routs_catalog (id, actual);

create index actual_entity_id
    on routs_catalog (entity_id, actual);

grant insert, select, update on routs_catalog to tg_user;

create table tg_message_log
(
    id                  integer generated by default as identity,
    dadd                timestamp default now(),
    chat_id             bigint,
    message_id          bigint,
    is_bot              boolean,
    has_inline_keyboard boolean
);

alter table tg_message_log
    owner to postgres;

create unique index tg_message_log_user_tg_id_meesage_id_uindex
    on tg_message_log (chat_id, message_id);

grant insert, select, update on tg_message_log to tg_user;

create table user_finished_lessons
(
    id        integer generated by default as identity,
    dadd      timestamp default now(),
    actual    boolean   default true,
    user_id   integer,
    lesson_id integer
);

alter table user_finished_lessons
    owner to postgres;

create unique index user_finished_lessons_id_user_id_lesson_id_actual_uindex
    on user_finished_lessons (id, user_id, lesson_id, actual);

