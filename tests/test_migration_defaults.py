"""The installed library must not acquire migrations from a project's defaults."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize("default", ["AutoField", "BigAutoField"])
def test_migrations_match_project_default(default):
    script = f"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
import tests.settings
tests.settings.DEFAULT_AUTO_FIELD = 'django.db.models.{default}'
import django
django.setup()
from django.core.management import call_command
call_command('makemigrations', check=True, dry_run=True)
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No changes detected" in result.stdout
