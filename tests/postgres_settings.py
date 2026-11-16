"""Optional disposable PostgreSQL database for generic identity regressions."""

import os

import environ

from .settings import *  # noqa: F401,F403

DATABASES = {"default": environ.Env.db_url_config(os.environ["FILEPOND_TEST_DATABASE_URL"])}
