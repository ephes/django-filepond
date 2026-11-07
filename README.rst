=============================
Django Filepond
=============================

.. image:: https://badge.fury.io/py/django-filepond.svg
    :target: https://badge.fury.io/py/django-filepond

.. image:: https://github.com/ephes/django-filepond/actions/workflows/tests.yml/badge.svg?branch=develop
    :target: https://github.com/ephes/django-filepond/actions/workflows/tests.yml

Django support for the JavaScript file upload library filepond

Documentation
-------------

The full documentation is at https://django-filepond.readthedocs.io.

Quickstart
----------

Install Django Filepond::

    pip install django-filepond

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'filepond.apps.FilepondConfig',
        ...
    )

Add Django Filepond's URL patterns:

.. code-block:: python

    from django.urls import include, path
    from filepond import urls as filepond_urls


    urlpatterns = [
        ...
        path('', include(filepond_urls)),
        ...
    ]

Cookie-authenticated uploads and reverts require Django CSRF protection.
Configure Filepond's process and revert requests to send ``X-CSRFToken``;
see ``docs/usage.rst`` for the client configuration, status codes and the
transaction/storage deletion guarantees.

Features
--------

* TODO

Running Tests
-------------

Install test/developer tools, then run the explicit compatibility matrix::

    python -m pip install -e '.[test,dev]'
    python -m tox

The matrix runs Python 3.10, 3.11 and 3.12 with Django 4.2 and 5.2, plus
Python 3.12 with Django 6.1. All listed interpreters are required for the full
local matrix; to run only one installed interpreter, use e.g.::

    python -m tox -e py312-django52

Each environment installs the wheel with test extras, verifies the Django
version, copies synthetic tests into an isolated directory, checks packaged
templates/static assets/migrations, applies fresh migrations and runs real
session-authenticated upload/revert tests with temporary media and SQLite.
Tests import the installed package, so missing distribution resources fail.
The library keeps its existing AutoField key even in BigAutoField projects;
regressions check both project defaults for migration drift.
Django 4.2 is retained for compatibility testing; choose a maintained Django
series for applications. No external storage, codec, browser or database
service is required. No type-checking configuration is currently maintained.

GitHub Actions runs this matrix on pushes and pull requests with read-only
repository permissions, plus the following lint and build/install checks::

    python -m black --check filepond tests testapp scripts
    python -m isort --check-only filepond tests testapp scripts
    python -m flake8 filepond tests testapp scripts
    python -m build
    python -m tox -e py312-django52 --recreate --installpkg dist/*.whl
    python -m tox -e py312-django52 --recreate --installpkg dist/*.tar.gz

The last two commands are shell examples; pass the single artifact path if
your shell does not expand wildcards. Both wheel and sdist installs run the
same migrations, resource smoke and upload suite. CI does not publish anything.

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
