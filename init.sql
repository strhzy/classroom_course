CREATE DATABASE file_manager_db;
\c file_manager_db;


-- file_manager_tag: Тег файла
CREATE TABLE IF NOT EXISTS file_manager_tag
(
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) NOT NULL
);

-- file_manager_file: Файл пользователя
CREATE TABLE IF NOT EXISTS file_manager_file
(
    id BIGSERIAL PRIMARY KEY,
    uploaded_by_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    file VARCHAR(100),
    file_type VARCHAR(10) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_provider VARCHAR(20) NOT NULL,
    yandex_path VARCHAR(1024) NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version INTEGER NOT NULL,
    visibility VARCHAR(10) NOT NULL,
    extracted_text TEXT,
    has_preview BOOLEAN NOT NULL,
    download_count INTEGER NOT NULL,
    importance VARCHAR(20) NOT NULL
);
CREATE INDEX file_manager_file_uploaded_by_at_idx ON file_manager_file (uploaded_by_id, uploaded_at DESC);
CREATE INDEX file_manager_file_file_type_idx ON file_manager_file (file_type);
CREATE INDEX file_manager_file_visibility_idx ON file_manager_file (visibility);

-- file_manager_file_tags: Связь «файл — теги»
CREATE TABLE IF NOT EXISTS file_manager_file_tags
(
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES file_manager_tag(id) ON DELETE CASCADE,
    UNIQUE (file_id, tag_id)
);

-- file_manager_file_shared_with: Связь «файл — с кем поделились»
CREATE TABLE IF NOT EXISTS file_manager_file_shared_with
(
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    UNIQUE (file_id, user_id)
);

-- file_manager_file_favorite: Связь «файл — избранное»
CREATE TABLE IF NOT EXISTS file_manager_file_favorite
(
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    UNIQUE (file_id, user_id)
);

-- file_manager_filecomment: Комментарий к файлу
CREATE TABLE IF NOT EXISTS file_manager_filecomment
(
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    parent_id BIGINT REFERENCES file_manager_filecomment(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- file_manager_fileversion: Версия файла (с blob и снапшотом)
CREATE TABLE IF NOT EXISTS file_manager_fileversion
(
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    changed_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    version_number INTEGER NOT NULL,
    version_file VARCHAR(100),
    change_description TEXT NOT NULL,
    snapshot_title VARCHAR(255) NOT NULL,
    snapshot_size BIGINT NOT NULL,
    snapshot_storage_provider VARCHAR(20) NOT NULL,
    snapshot_storage_path VARCHAR(1024) NOT NULL,
    has_blob BOOLEAN NOT NULL,
    blob_storage_provider VARCHAR(20) NOT NULL,
    blob_storage_path VARCHAR(1024) NOT NULL,
    blob_size BIGINT NOT NULL,
    blob_sha256 VARCHAR(64) NOT NULL,
    extracted_text_snapshot TEXT NOT NULL,
    structured_snapshot JSONB,
    structured_schema_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- file_manager_fileactivity: Журнал активности с файлом
CREATE TABLE IF NOT EXISTS file_manager_fileactivity
(
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT REFERENCES file_manager_file(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    activity_type VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX file_manager_fileactivity_user_at_idx ON file_manager_fileactivity (user_id, created_at DESC);
CREATE INDEX file_manager_fileactivity_type_at_idx ON file_manager_fileactivity (activity_type, created_at DESC);

-- file_manager_userstoragequota: Квота хранилища пользователя
CREATE TABLE IF NOT EXISTS file_manager_userstoragequota
(
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
    total_quota_bytes BIGINT NOT NULL,
    used_bytes BIGINT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL
);

-- file_manager_externalstorageconnection: Подключение к внешнему хранилищу (Яндекс.Диск)
CREATE TABLE IF NOT EXISTS file_manager_externalstorageconnection
(
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (user_id, provider)
);

-- file_manager_favoritecollection: Коллекция избранного
CREATE TABLE IF NOT EXISTS file_manager_favoritecollection
(
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    title VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (user_id, title)
);

-- file_manager_favoritecollectionitem: Файл в коллекции избранного
CREATE TABLE IF NOT EXISTS file_manager_favoritecollectionitem
(
    id BIGSERIAL PRIMARY KEY,
    collection_id BIGINT NOT NULL REFERENCES file_manager_favoritecollection(id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (collection_id, file_id)
);

-- file_manager_sharedworkspace: Совместная рабочая область (workspace)
CREATE TABLE IF NOT EXISTS file_manager_sharedworkspace
(
    id BIGSERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    title VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- file_manager_sharedworkspace_files: Связь «область — файлы»
CREATE TABLE IF NOT EXISTS file_manager_sharedworkspace_files
(
    id BIGSERIAL PRIMARY KEY,
    sharedworkspace_id BIGINT NOT NULL REFERENCES file_manager_sharedworkspace(id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES file_manager_file(id) ON DELETE CASCADE,
    UNIQUE (sharedworkspace_id, file_id)
);

-- file_manager_sharedworkspace_participants: Связь «область — участники»
CREATE TABLE IF NOT EXISTS file_manager_sharedworkspace_participants
(
    id BIGSERIAL PRIMARY KEY,
    sharedworkspace_id BIGINT NOT NULL REFERENCES file_manager_sharedworkspace(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    UNIQUE (sharedworkspace_id, user_id)
);

-- Системные таблицы Django
-- auth_user: Пользователь системы (django.contrib.auth)
CREATE TABLE IF NOT EXISTS auth_user
(
    id BIGSERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    date_joined TIMESTAMPTZ NOT NULL
);

-- auth_group: Группа пользователей
CREATE TABLE IF NOT EXISTS auth_group
(
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

-- auth_permission: Разрешение Django
CREATE TABLE IF NOT EXISTS auth_permission
(
    id BIGSERIAL PRIMARY KEY,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id) ON DELETE CASCADE,
    codename VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    UNIQUE (content_type_id, codename)
);

-- auth_user_groups: Связь «пользователи — группы»
CREATE TABLE IF NOT EXISTS auth_user_groups
(
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    UNIQUE (user_id, group_id)
);

-- auth_user_user_permissions: Связь «пользователи — разрешения»
CREATE TABLE IF NOT EXISTS auth_user_user_permissions
(
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE (user_id, permission_id)
);

-- auth_group_permissions: Связь «группы — разрешения»
CREATE TABLE IF NOT EXISTS auth_group_permissions
(
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE (group_id, permission_id)
);

-- django_content_type: Тип содержимого Django
CREATE TABLE IF NOT EXISTS django_content_type
(
    id BIGSERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE (app_label, model)
);

-- django_session: Сессия пользователя
CREATE TABLE IF NOT EXISTS django_session
(
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMPTZ NOT NULL
);
CREATE INDEX django_session_expire_date_idx ON django_session (expire_date);

-- django_migrations: История применённых миграций
CREATE TABLE IF NOT EXISTS django_migrations
(
    id BIGSERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMPTZ NOT NULL
);

-- django_admin_log: Журнал действий администратора
CREATE TABLE IF NOT EXISTS django_admin_log
(
    id BIGSERIAL PRIMARY KEY,
    object_id TEXT,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL,
    change_message TEXT NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    action_time TIMESTAMPTZ NOT NULL
);