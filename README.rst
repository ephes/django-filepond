=============================
Django Filepond
=============================

.. image:: https://badge.fury.io/py/django-filepond.svg
    :target: https://badge.fury.io/py/django-filepond

.. image:: https://travis-ci.org/ephes/django-filepond.svg?branch=master
    :target: https://travis-ci.org/ephes/django-filepond

.. image:: https://codecov.io/gh/ephes/django-filepond/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/ephes/django-filepond

Django support for the fjavascript file upload library filepond

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

    from filepond import urls as filepond_urls


    urlpatterns = [
        ...
        url(r'^', include(filepond_urls)),
        ...
    ]

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
