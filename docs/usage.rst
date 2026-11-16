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
storage deletion are not an atomic operation. Linked reverts resolve the unique
FileField matching the registered key and use that field's storage, never the
Upload field's default backend. Ambiguous linked
registrations receive 400 and roll back; ambiguous or missing linked targets
receive 409 on revert with no deletion. Additional linked-model files
are outside this upload's ownership and are left alone.

Storage failures are logged to ``filepond.views`` after the rows commit;
revert still returns 200. There is no durable cleanup queue or automatic retry.
Monitor these logs and retry failed keys after checking for surviving
references. A process crash between database commit and cleanup can also
leave an orphan. Database rollback always retains the original bytes.

Upload handlers and responses
-----------------------------

``/process`` stores an Upload directly. ``/process/<app_label>`` accepts an
installed application's label only when its application module (usually
``__init__.py``) exposes a callable ``upload_handler(request)``. The hook returns
``(ModelFormClass, context)``; ``get_model_form`` in ``filepond.forms`` builds
this pair with ``upload_field_name`` and optional ``user_field``. To update an
existing object, add ``instance`` to context. With ``user_field`` configured,
Filepond checks the persisted owner on the write database before any storage or
model save; foreign instances
receive 404. A mutable instance returned by the hook cannot override that check.
The hook remains responsible for other application permissions. Without
``user_field``, the hook must authorize the instance itself; Filepond cannot
infer ownership for ownerless models.

A linked revert deletes its object (including a pre-existing object) only when
the registration still uniquely matches the current file key and no other
Upload registration refers to that object. Stale generations and other
registrations, regardless of owner, receive 409 without changing rows or files.
The application must reconcile conflicting registrations through its authorized
object lifecycle. Revert does not restore previous file or object state.

Send exactly one file under ``filepond`` or ``original``. Missing, unexpected
or multiple files receive 400 (``Invalid upload``) before any handler runs.
The hook sees the file as ``request.FILES['original']``; Filepond then maps it
to the configured model field. Unsupported applications receive 404 for valid
file requests. Exceptions inside a registered hook remain application errors;
validate application-specific input in the hook or form rather than relying
on route error handling. Successful uploads return 201 with the Upload ID.

Linked models must use integer primary keys in the positive signed 64-bit
domain (1 through 2**63 - 1). AutoField and BigAutoField are supported; UUID,
text, boolean, zero and negative identities receive 400 before storage writes.
Apply the ``filepond`` migrations to widen existing generic registration keys;
existing AutoField registrations remain valid.

The linked model and Upload registration save in one transaction on the linked
model's write database (or Upload's database for the default handler). All
linked rows, users, content types and form relations must be available on that
same database; configure routers accordingly. On a failure within this save,
the rows roll back and newly saved incoming file keys are removed through the
storage API if no surviving registered FileField references them. Existing
keys are retained, including a replaced instance's previous file. Successful
replacement retires previous keys only after commit and only when no surviving
registered FileField on the same database and storage instance references them.
This includes old Upload wrappers on that storage: a key still registered by
another Upload is retained. Cleanup failures use the same logging and manual
retry contract as revert.

Storage must allocate fresh keys without overwriting existing bytes. Shared
backends must reuse the same storage instance, with the same reference and
concurrency restrictions described for revert above. Custom model save hooks
must not create extra files or eagerly delete old files. Incoming files are
saved before the model's save hooks/signals run, so ``upload_to`` must not depend
on state those hooks set. Database transactions cannot roll back storage writes:
cleanup is best effort and logs failures for manual retry. A crash or a storage
save that writes then raises without returning its key can leave orphaned files;
there is no rollback callback or durable cleanup queue.

Upload transaction boundary
---------------------------

Uploads require autocommit with no enclosing atomic block on the selected write
database. Filepond checks this before saving storage keys and uses an outermost
durable transaction, so a successful response confirms the database commit.
An enclosing ``transaction.atomic()``, disabled autocommit or ``ATOMIC_REQUESTS``
on that database receives 400 before storage writes. There is no Django
rollback callback to compensate a later host transaction rollback. Revert can
still run inside an outer transaction: it only deletes storage after commit.

If your host enables ``ATOMIC_REQUESTS``, mount the upload view explicitly with
Django's public ``non_atomic_requests`` decorator on the selected database:

.. code-block:: python

    from django.db import transaction
    from django.urls import path
    from filepond.views import UploadCreateView

    process = transaction.non_atomic_requests(using="default")(UploadCreateView.as_view())
    urlpatterns = [path("process", process, name="process")]

Apply the same wrapper to custom application upload routes; use the routed
write alias instead of ``default`` when appropriate. This opts the upload
endpoint out of the host request transaction. Application hooks and form
validation must not write files or make unrelated database mutations before
Filepond admits the upload boundary. Tests exercising successful uploads must
use ``TransactionTestCase`` or ``pytest.mark.django_db(transaction=True)``.

Detail access
-------------

``/get/<id>/<size>/`` requires login and resolves only Uploads belonging to the
requesting user. Foreign and nonexistent IDs both return 404; anonymous requests
redirect to login. Authentication alone does not authorize another user's
upload. The host still supplies ``filepond/upload_detail.html`` and controls
its rendering; this view does not itself stream file bytes. Storage URLs must
have their own appropriate access policy.
