"""Fail if tox loads the checkout or installs an incomplete distribution."""

import os
import sysconfig
from importlib.resources import files
from pathlib import Path

import django
from django.template.loader import get_template

import filepond

assert (
    Path(filepond.__file__).resolve().is_relative_to(Path(sysconfig.get_path("purelib")).resolve())
), filepond.__file__
assert django.VERSION[:2] == tuple(map(int, os.environ["EXPECTED_DJANGO"].split("."))), django.get_version()
django.setup()
get_template("filepond/upload_form.html")
for resource in (
    "migrations/0001_initial.py",
    "migrations/0002_auto_20181127_0925.py",
    "migrations/0003_auto_20181127_0938.py",
    "static/js/filepond.js",
    "static/css/filepond.css",
):
    assert files("filepond").joinpath(resource).is_file(), resource
print(f"Installed distribution: Django {django.get_version()}, templates, migrations and static assets present")
