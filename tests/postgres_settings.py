"""Optional disposable PostgreSQL database for generic identity regressions."""

import os

import environ

from .settings import *  # noqa: F401,F403

_database = environ.Env.db_url_config(os.environ["FILEPOND_TEST_DATABASE_URL"])
# The second alias mirrors tests.settings for linked-model write routing tests.
DATABASES = {
    "default": _database,
    "uploads": {**_database, "TEST": {"NAME": f"test_{_database['NAME']}_uploads"}},
}

# PostgreSQL creates foreign keys immediately, so the synthetic test app cannot stay
# unmigrated: it references the migrated auth user table. Its schema is kept beside
# these settings so the SQLite matrix and the migration-default checks keep the app
# unmigrated.
MIGRATION_MODULES = {"testapp": "tests.postgres_testapp_migrations"}
