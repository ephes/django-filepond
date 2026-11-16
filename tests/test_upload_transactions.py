from unittest.mock import patch

import pytest
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from django.urls import reverse

from filepond.forms import get_model_form
from filepond.models import Upload
from testapp.models import LocalAudio

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("linked", [False, True])
@pytest.mark.parametrize("boundary", ["atomic", "atomic-requests", "manual-autocommit"])
def test_enclosing_transaction_refused_before_storage(client, user, linked, boundary):
    client.force_login(user)
    model, field = (LocalAudio, "m4a") if linked else (Upload, "original")
    url = reverse("filepond:process", kwargs={"app_name": "testapp"}) if linked else reverse("filepond:process")
    storage = InMemoryStorage()
    with patch.object(model._meta.get_field(field), "storage", storage):
        instance = model.objects.create(**{("owner" if linked else "user"): user, field: "old.m4a"})
        form_class, context = get_model_form(model, upload_field_name=field, user_field="owner" if linked else "user")
        context["instance"] = instance
        # The default handler normally creates a new Upload; also exercise a linked update.
        with (
            patch("testapp.upload_handler", return_value=(form_class, context)),
            patch.object(storage, "save", wraps=storage.save) as save,
        ):

            def post():
                response = client.post(url, {"original": SimpleUploadedFile("new.m4a", b"new")})
                assert response.status_code == 400
                assert response.content == b"Upload requires autocommit outside an atomic block"
                save.assert_not_called()

            if boundary == "atomic":
                with pytest.raises(RuntimeError, match="outer rollback"):
                    with transaction.atomic():
                        post()
                        raise RuntimeError("outer rollback")
            elif boundary == "atomic-requests":
                with patch.dict(connection.settings_dict, {"ATOMIC_REQUESTS": True}):
                    post()
            else:
                transaction.set_autocommit(False)
                try:
                    post()
                finally:
                    transaction.rollback()
                    transaction.set_autocommit(True)
        instance.refresh_from_db()
        assert getattr(instance, field).name == "old.m4a"
        assert model.objects.count() == 1
        assert Upload.objects.count() == (0 if linked else 1)


def test_non_atomic_request_mount_allows_committed_upload(client, user, settings):
    from django.urls import path

    from filepond.views import UploadCreateView

    global urlpatterns
    urlpatterns = [
        path("non-atomic-process", transaction.non_atomic_requests(using="default")(UploadCreateView.as_view()))
    ]
    settings.ROOT_URLCONF = __name__
    client.force_login(user)
    with patch.dict(connection.settings_dict, {"ATOMIC_REQUESTS": True}):
        response = client.post("/non-atomic-process", {"original": SimpleUploadedFile("new.bin", b"new")})
    assert response.status_code == 201
    assert not connection.in_atomic_block
    upload = Upload.objects.get(pk=int(response.content))
    assert upload.original.read() == b"new"


def test_commit_failure_compensates_new_storage_keys(client, user):
    from django.db import IntegrityError

    client.force_login(user)
    storage = InMemoryStorage()
    with (
        patch.object(Upload._meta.get_field("original"), "storage", storage),
        patch.object(connection, "commit", side_effect=IntegrityError("commit failed")),
    ):
        with pytest.raises(IntegrityError, match="commit failed"):
            client.post(reverse("filepond:process"), {"original": SimpleUploadedFile("new.bin", b"new")})
    assert not Upload.objects.exists()
    assert not storage.exists("uploads/new.bin")
