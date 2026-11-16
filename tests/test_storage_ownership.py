from unittest.mock import patch

import pytest
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from filepond.models import Upload
from testapp.models import LocalAudio

pytestmark = pytest.mark.django_db
PROCESS = reverse("filepond:process", kwargs={"app_name": "testapp"})
REVERT = reverse("filepond:revert")


def test_linked_revert_uses_source_storage(client, user, django_capture_on_commit_callbacks):
    client.force_login(user)
    source, default = InMemoryStorage(), InMemoryStorage()
    with (
        patch.object(LocalAudio._meta.get_field("m4a"), "storage", source),
        patch.object(Upload._meta.get_field("original"), "storage", default),
    ):
        response = client.post(PROCESS, {"original": SimpleUploadedFile("sample.m4a", b"owned")})
        assert response.status_code == 201
        upload = Upload.objects.get(pk=int(response.content))
        name = upload.original.name
        default.save(name, SimpleUploadedFile("sample.m4a", b"unrelated"))
        with django_capture_on_commit_callbacks(execute=True):
            assert client.post(REVERT, str(upload.pk), content_type="text/plain").status_code == 200
            assert source.exists(name)
        assert not source.exists(name)
        assert default.open(name).read() == b"unrelated"
        assert not LocalAudio.objects.exists()
        assert not Upload.objects.exists()


def test_ambiguous_linked_revert_is_refused(client, user):
    client.force_login(user)
    audio = LocalAudio.objects.create(owner=user, m4a=SimpleUploadedFile("sample.m4a", b"owned"))
    audio.mp3 = audio.m4a.name
    audio.save()
    upload = Upload.objects.create(user=user, original=audio.m4a.name, content_object=audio)
    assert client.post(REVERT, str(upload.pk), content_type="text/plain").status_code == 409
    assert Upload.objects.filter(pk=upload.pk).exists()
    assert LocalAudio.objects.filter(pk=audio.pk).exists()
    assert audio.m4a.read() == b"owned"


def test_ambiguous_linked_registration_rolls_back(client, user):
    client.force_login(user)
    original_save = LocalAudio.save
    storage = InMemoryStorage()

    def ambiguous_save(instance, *args, **kwargs):
        instance.mp3 = instance.m4a.name
        original_save(instance, *args, **kwargs)

    with (
        patch.object(LocalAudio._meta.get_field("m4a"), "storage", storage),
        patch.object(LocalAudio, "save", ambiguous_save),
    ):
        response = client.post(PROCESS, {"original": SimpleUploadedFile("sample.m4a", b"owned")})
        assert response.status_code == 400
        assert not storage.exists("testapp/audio/sample.m4a")
    assert not Upload.objects.exists()
    assert not LocalAudio.objects.exists()
