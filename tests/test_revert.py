from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.middleware.csrf import get_token
from django.test import Client, RequestFactory
from django.urls import reverse

from filepond.models import Upload
from testapp.models import LocalAudio

pytestmark = pytest.mark.django_db
PROCESS = reverse("filepond:process")
REVERT = reverse("filepond:revert")


def owned_upload(user, linked=False):
    upload = Upload.objects.create(user=user, original=SimpleUploadedFile("sample.bin", b"synthetic"))
    if linked:
        audio = LocalAudio.objects.create(owner=user, m4a=upload.original.name)
        upload.content_object = audio
        upload.save()
    return upload


def revert(client, upload):
    return client.post(REVERT, str(upload.pk), content_type="text/plain")


@pytest.mark.parametrize("url", [PROCESS, reverse("filepond:process", kwargs={"app_name": "testapp"}), REVERT])
def test_cookie_mutations_require_csrf(user, url):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    if url == REVERT:
        upload = owned_upload(user)
        assert client.post(url, str(upload.pk), content_type="text/plain").status_code == 403
        assert client.delete(url, str(upload.pk), content_type="text/plain").status_code == 403
    else:
        assert client.post(url, {"filepond": SimpleUploadedFile("test.m4a", b"synthetic")}).status_code == 403


def test_valid_csrf_upload_and_owned_revert(user, user2):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    request = RequestFactory().get("/")
    csrf_value = get_token(request)
    client.cookies["csrftoken"] = request.META["CSRF_COOKIE"]
    client.defaults["HTTP_X_CSRFTOKEN"] = csrf_value
    response = client.post(PROCESS, {"filepond": SimpleUploadedFile("test.bin", b"synthetic")})
    assert response.status_code == 201
    upload = Upload.objects.get(pk=int(response.content))
    foreign = owned_upload(user2, linked=True)
    assert revert(client, foreign).status_code == 404
    assert Upload.objects.filter(pk=foreign.pk).exists()
    assert LocalAudio.objects.filter(pk=foreign.object_id).exists()
    assert foreign.original.storage.exists(foreign.original.name)
    assert revert(client, upload).status_code == 200


@pytest.mark.parametrize(
    "body",
    [b"", b"abc", b"-1", b"0", b"1.0", b"1" * 10000, b"9223372036854775808", b" 1", b"+1", b"\xff", b"\xd9\xa1"],
)
def test_invalid_revert_ids(client, user, body):
    client.force_login(user)
    assert client.post(REVERT, body, content_type="text/plain").status_code == 400


def test_missing_revert_id(client, user):
    client.force_login(user)
    assert client.post(REVERT, "123456", content_type="text/plain").status_code == 404


@pytest.mark.parametrize("linked", [False, True])
def test_storage_delete_after_commit(client, user, linked, django_capture_on_commit_callbacks):
    client.force_login(user)
    upload = owned_upload(user, linked)
    storage, name, pk, linked_pk = upload.original.storage, upload.original.name, upload.pk, upload.object_id
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        assert revert(client, upload).status_code == 200
        assert storage.exists(name)
        assert not Upload.objects.filter(pk=pk).exists()
        if linked:
            assert not LocalAudio.objects.filter(pk=linked_pk).exists()
    assert len(callbacks) == 1
    assert not storage.exists(name)


def test_linked_deletions_roll_back_together(client, user, django_capture_on_commit_callbacks):
    client.force_login(user)
    upload = owned_upload(user, linked=True)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with patch.object(Upload, "delete", side_effect=RuntimeError("injected")) as deletion:
            with pytest.raises(RuntimeError, match="injected"):
                revert(client, upload)
            deletion.assert_called_once()
    assert callbacks == []
    assert Upload.objects.filter(pk=upload.pk).exists()
    assert LocalAudio.objects.filter(pk=upload.object_id).exists()
    assert upload.original.storage.exists(upload.original.name)


def test_outer_rollback_keeps_storage(client, user, django_capture_on_commit_callbacks):
    client.force_login(user)
    upload = owned_upload(user, linked=True)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                assert revert(client, upload).status_code == 200
                raise RuntimeError("rollback")
    assert callbacks == []
    assert Upload.objects.filter(pk=upload.pk).exists()
    assert LocalAudio.objects.filter(pk=upload.object_id).exists()
    assert upload.original.storage.exists(upload.original.name)


@pytest.mark.parametrize("reference", ["upload", "linked-m4a", "linked-mp3"])
def test_shared_storage_survives(client, user, reference, django_capture_on_commit_callbacks):
    client.force_login(user)
    upload = owned_upload(user, linked=True)
    name = upload.original.name
    if reference == "upload":
        survivor = Upload.objects.create(user=user, original=name)
    else:
        survivor = LocalAudio.objects.create(owner=user, **{reference.split("-")[1]: name})
    with django_capture_on_commit_callbacks(execute=True):
        assert revert(client, upload).status_code == 200
    assert type(survivor).objects.filter(pk=survivor.pk).exists()
    assert upload.original.storage.exists(name)


def test_storage_failure_is_logged_after_database_commit(client, user, django_capture_on_commit_callbacks, caplog):
    client.force_login(user)
    upload = owned_upload(user)
    with patch.object(upload.original.storage, "delete", side_effect=OSError("storage unavailable")) as deletion:
        with django_capture_on_commit_callbacks(execute=True):
            assert revert(client, upload).status_code == 200
        deletion.assert_called_once_with(upload.original.name)
    assert not Upload.objects.filter(pk=upload.pk).exists()
    assert upload.original.storage.exists(upload.original.name)
    assert "storage" in caplog.text


@pytest.mark.django_db(transaction=True)
def test_delete_method_commits_storage_cleanup(client, user):
    client.force_login(user)
    upload = owned_upload(user, linked=True)
    storage, name = upload.original.storage, upload.original.name
    assert client.delete(REVERT, str(upload.pk), content_type="text/plain").status_code == 200
    assert not Upload.objects.filter(pk=upload.pk).exists()
    assert not LocalAudio.objects.filter(pk=upload.object_id).exists()
    assert not storage.exists(name)
