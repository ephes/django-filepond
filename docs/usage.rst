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

    from django.urls import include, path
    from filepond import urls as filepond_urls


    urlpatterns = [
        ...
        path('', include(filepond_urls)),
        ...
    ]

Session authentication and CSRF
-------------------------------

Keep Django's ``CsrfViewMiddleware`` enabled. Upload and revert require login
and a valid CSRF token. Existing clients must send ``X-CSRFToken`` on both
requests; tokenless requests now receive 403. Render ``{% csrf_token %}`` in
the page's form and configure the client on that same-origin page:

.. code-block:: javascript

    const csrfValue = document.querySelector('[name=csrfmiddlewaretoken]').value;
    FilePond.create(document.querySelector('input[type=file]'), {
        server: {
            process: {url: '/process', headers: {'X-CSRFToken': csrfValue}},
            revert: {url: '/revert/', headers: {'X-CSRFToken': csrfValue}}
        }
    });

The DOM token also works with HttpOnly CSRF cookies and session-based CSRF.
Use your mounted URL prefix, and keep credentials and tokens on the same
origin. Revert accepts DELETE (Filepond's default) or POST with the upload ID
as the raw request body.

Revert guarantees and storage ownership
---------------------------------------

IDs must contain 1–19 ASCII digits and be positive signed 64-bit integers.
Malformed or out-of-range IDs receive 400. Missing IDs and IDs owned by another
user both receive 404. Successful revert returns an empty 200 response.

Revert deletes the owned Upload and its linked application object in one
transaction on the Upload write database. Linked models must use that same
database. Database failures roll back both deletions. File storage deletion
runs only after the outer transaction commits, using the storage API rather
than a local filesystem path. Linked models must not delete files eagerly in
delete hooks/signals: such side effects cannot be rolled back by Django.

The original upload key is removed only if no surviving registered FileField
on the same database and storage instance references that name (including
other Uploads and linked-model fields). Custom storage fields sharing a
backend must reuse the same storage instance. References outside registered
models or databases are not discoverable: do not share upload-owned keys with
them. Do not concurrently reuse a key during revert; reference checks and
storage deletion are not an atomic operation. Additional linked-model files
are outside this upload's ownership and are left alone.

Storage failures are logged to ``filepond.views`` after the rows commit;
revert still returns 200. There is no durable cleanup queue or automatic retry.
Monitor these logs and retry failed keys after checking for surviving
references. A process crash between database commit and cleanup can also
leave an orphan. Database rollback always retains the original bytes.
