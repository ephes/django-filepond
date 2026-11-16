from unittest.mock import patch

import pytest
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from filepond.forms import get_model_form
from filepond.models import Upload
from testapp.models import LocalAudio

pytestmark = pytest.mark.django_db(transaction=True)
PROCESS = reverse("filepond:process", kwargs={"app_name": "testapp"})
REVERT = reverse("filepond:revert")


@pytest.mark.parametrize("disguise", [False, True])
def test_foreign_existing_instance_refused_before_storage(client, user, user2, disguise):
    client.force_login(user)
    storage = InMemoryStorage()
    with patch.object(LocalAudio._meta.get_field("m4a"), "storage", storage):
        audio = LocalAudio.objects.create(owner=user2, m4a=SimpleUploadedFile("private.m4a", b"private"))
        name = audio.m4a.name
        if disguise:
            # Admission must check persisted ownership, not a handler's mutable copy.
            audio.owner = user
        form_class, context = get_model_form(LocalAudio, upload_field_name="m4a", user_field="owner")
        context["instance"] = audio
        with (
            patch("testapp.upload_handler", return_value=(form_class, context)),
            patch.object(storage, "save", wraps=storage.save) as save,
        ):
            response = client.post(PROCESS, {"original": SimpleUploadedFile("new.m4a", b"replacement")})
            assert response.status_code == 404
            save.assert_not_called()
        audio.refresh_from_db()
        assert audio.owner == user2
        assert audio.m4a.name == name
        assert audio.m4a.read() == b"private"
        assert not Upload.objects.exists()


def test_stale_revert_preserves_new_upload_generation(client, user, django_capture_on_commit_callbacks):
    client.force_login(user)
    first = client.post(PROCESS, {"original": SimpleUploadedFile("first.m4a", b"first")})
    old = Upload.objects.get(pk=int(first.content))
    audio = old.content_object
    form_class, context = get_model_form(LocalAudio, upload_field_name="m4a", user_field="owner")
    context["instance"] = audio
    with patch("testapp.upload_handler", return_value=(form_class, context)):
        second = client.post(PROCESS, {"original": SimpleUploadedFile("second.m4a", b"second")})
    current = Upload.objects.get(pk=int(second.content))
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        assert client.post(REVERT, str(old.pk), content_type="text/plain").status_code == 409
    assert callbacks == []
    audio.refresh_from_db()
    assert audio.m4a.name == current.original.name
    assert audio.m4a.read() == b"second"
    assert Upload.objects.filter(pk__in=[old.pk, current.pk]).count() == 2


@pytest.mark.parametrize("other_owner", [False, True])
def test_current_revert_preserves_other_linked_registrations(client, user, user2, other_owner):
    client.force_login(user)
    audio = LocalAudio.objects.create(owner=user, m4a=SimpleUploadedFile("shared.m4a", b"shared"))
    upload = Upload.objects.create(user=user, original=audio.m4a.name, content_object=audio)
    other = Upload.objects.create(user=user2 if other_owner else user, original=audio.m4a.name, content_object=audio)
    assert client.post(REVERT, str(upload.pk), content_type="text/plain").status_code == 409
    assert Upload.objects.filter(pk__in=[upload.pk, other.pk]).count() == 2
    assert LocalAudio.objects.filter(pk=audio.pk).exists()
    assert audio.m4a.read() == b"shared"
