=====
Usage
=====

To use Django Filepond in a project, add it to your `INSTALLED_APPS`:

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
