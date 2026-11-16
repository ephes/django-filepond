from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse

from filepond.forms import get_model_form
from filepond.models import Upload
from testapp.models import BigAudio, LocalAudio, TextAudio

pytestmark = pytest.mark.django_db(transaction=True)
PROCESS = reverse("filepond:process", kwargs={"app_name": "testapp"})
REVERT = reverse("filepond:revert")


@pytest.mark.parametrize("identity", [2**32 + 17, 2**63 - 1])
def test_bigint_registration_and_revert(client, user, identity, django_capture_on_commit_callbacks):
    client.force_login(user)
    form_class, context = get_model_form(BigAudio, user_field="owner")
    context["instance"] = BigAudio(pk=identity)
    with patch("testapp.upload_handler", return_value=(form_class, context)):
        response = client.post(PROCESS, {"original": SimpleUploadedFile("big.bin", b"synthetic")})
    assert response.status_code == 201
    upload = Upload.objects.get(pk=int(response.content))
    assert upload.object_id == identity
    assert upload.content_object == BigAudio.objects.get(pk=identity)
    storage, name = upload.content_object.original.storage, upload.original.name
    with django_capture_on_commit_callbacks(execute=True):
        assert client.post(REVERT, str(upload.pk), content_type="text/plain").status_code == 200
    assert not BigAudio.objects.filter(pk=identity).exists()
    assert not storage.exists(name)


@pytest.mark.parametrize(
    "model,identity", [(TextAudio, "synthetic"), (BigAudio, 0), (BigAudio, -1), (BigAudio, 2**63), (BigAudio, True)]
)
def test_unsupported_identity_refused_before_storage(client, user, model, identity):
    client.force_login(user)
    storage = InMemoryStorage()
    form_class, context = get_model_form(model, user_field="owner")
    context["instance"] = model(pk=identity)
    with (
        patch("testapp.upload_handler", return_value=(form_class, context)),
        patch.object(model._meta.get_field("original"), "storage", storage),
        patch.object(storage, "save", wraps=storage.save) as save,
    ):
        assert client.post(PROCESS, {"original": SimpleUploadedFile("big.bin", b"synthetic")}).status_code == 400
        save.assert_not_called()
    assert not Upload.objects.exists()
    assert not model.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_bigint_migration_preserves_existing_generic_link(user):
    audio = LocalAudio.objects.create(owner=user, m4a="testapp/audio/existing.m4a")
    content_type = ContentType.objects.get_for_model(LocalAudio)
    executor = MigrationExecutor(connection)
    old = [("filepond", "0003_auto_20181127_0938")]
    new = [("filepond", "0004_upload_object_id_bigint")]
    executor.migrate(old)
    try:
        old_upload = executor.loader.project_state(old).apps.get_model("filepond", "Upload")
        registration = old_upload.objects.create(
            user_id=user.pk, original=audio.m4a.name, content_type_id=content_type.pk, object_id=audio.pk
        )
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(new)
    upload = Upload.objects.get(pk=registration.pk)
    assert upload.content_object == audio
    # Saving through historical models exercises the migrated portable field domain.
    new_upload = executor.loader.project_state(new).apps.get_model("filepond", "Upload")
    bigint = new_upload.objects.create(user_id=user.pk, original="big.bin", object_id=2**32 + 17)
    assert new_upload.objects.get(pk=bigint.pk).object_id == 2**32 + 17
    assert new_upload._meta.get_field("object_id").get_internal_type() == "PositiveBigIntegerField"
