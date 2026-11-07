from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.test import RequestFactory
from django.urls import reverse

from filepond.forms import get_model_form
from filepond.models import Upload
from filepond.views import UploadCreateView
from testapp.models import LocalAudio

pytestmark = pytest.mark.django_db
PROCESS = reverse("filepond:process", kwargs={"app_name": "testapp"})


def media_files(storage, directory=""):
    directories, files = storage.listdir(directory)
    paths = [f"{directory}/{name}".lstrip("/") for name in files]
    for child in directories:
        paths.extend(media_files(storage, f"{directory}/{child}".lstrip("/")))
    return paths


def test_detail_is_owner_scoped(client, user, user2, settings):
    settings.TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "OPTIONS": {
                "loaders": [
                    ("django.template.loaders.locmem.Loader", {"filepond/upload_detail.html": "{{ object.original }}"})
                ]
            },
        }
    ]
    upload = Upload.objects.create(user=user, original="uploads/private.bin")
    url = reverse("filepond:get", kwargs={"pk": upload.pk, "size": "original"})
    missing = reverse("filepond:get", kwargs={"pk": upload.pk + 100, "size": "original"})
    assert client.get(url).status_code == 302
    client.force_login(user)
    assert client.get(url).content == b"uploads/private.bin"
    client.force_login(user2)
    assert client.get(url).status_code == client.get(missing).status_code == 404


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", ["registration", "model-save"])
def test_failed_creation_rolls_back_and_cleans_only_new_bytes(client, user, existing, failure):
    client.force_login(user)
    # This storage has no filesystem path; cleanup must use the storage API.
    storage = InMemoryStorage()
    field = LocalAudio._meta.get_field("m4a")
    with patch.object(field, "storage", storage):
        previous = storage.save("testapp/audio/previous.m4a", SimpleUploadedFile("previous.m4a", b"old"))
        survivor = LocalAudio.objects.create(owner=user, m4a=previous)
        instance = LocalAudio.objects.create(owner=user, m4a=previous) if existing else None
        initial_count = LocalAudio.objects.count()
        form_class, context = get_model_form(LocalAudio, upload_field_name="m4a", user_field="owner")
        if existing:
            context["instance"] = instance
        handler = Mock(return_value=(form_class, context))
        target = QuerySet if failure == "registration" else LocalAudio
        method = "create" if failure == "registration" else "save"
        original_save = LocalAudio.save

        def fail_after_save(self, *args, **kwargs):
            original_save(self, *args, **kwargs)
            raise IntegrityError("injected save failure")

        effect = IntegrityError("injected registration failure") if failure == "registration" else fail_after_save
        with (
            patch("testapp.upload_handler", handler),
            patch.object(target, method, side_effect=effect, autospec=True) as save,
        ):
            with pytest.raises(IntegrityError, match="injected"):
                client.post(PROCESS, {"original": SimpleUploadedFile("previous.m4a", b"new")})
            save.assert_called_once()
        assert LocalAudio.objects.count() == initial_count
        assert not Upload.objects.exists()
        survivor.refresh_from_db()
        assert survivor.m4a.name == previous
        if instance:
            instance.refresh_from_db()
            assert instance.m4a.name == previous
        assert media_files(storage) == [previous]
        assert storage.open(previous).read() == b"old"


@pytest.mark.parametrize("input_name", ["filepond", "original"])
def test_valid_custom_upload(client, user, input_name):
    client.force_login(user)
    with patch("testapp.upload_handler", wraps=__import__("testapp").upload_handler) as handler:
        response = client.post(PROCESS, {input_name: SimpleUploadedFile("sample.m4a", b"synthetic")})
        handler.assert_called_once()
    assert response.status_code == 201
    upload = Upload.objects.get(pk=int(response.content))
    assert upload.content_object.m4a.name == upload.original.name
    assert upload.content_object.m4a.read() == b"synthetic"


@pytest.mark.parametrize("input_name", [None, "unrelated"])
def test_missing_upload_rejected_before_handler(client, user, input_name):
    client.force_login(user)
    data = {} if input_name is None else {input_name: SimpleUploadedFile("sample.m4a", b"synthetic")}
    with patch("testapp.upload_handler", wraps=__import__("testapp").upload_handler) as handler:
        response = client.post(PROCESS, data)
        assert response.status_code == 400
        assert response.content == b"Invalid upload"
        handler.assert_not_called()
    assert not LocalAudio.objects.exists()
    assert not Upload.objects.exists()


@pytest.mark.parametrize("app_name", ["unknown-app", "auth", "testapp"])
def test_unsupported_app_is_404(client, user, app_name):
    client.force_login(user)
    url = reverse("filepond:process", kwargs={"app_name": app_name})
    with patch("testapp.upload_handler", None):
        assert client.post(url, {"original": SimpleUploadedFile("sample.m4a", b"synthetic")}).status_code == 404
    assert not LocalAudio.objects.exists()
    assert not Upload.objects.exists()


def test_registered_handler_failure_propagates(client, user):
    client.force_login(user)
    with patch("testapp.upload_handler", side_effect=AttributeError("handler bug")) as handler:
        with pytest.raises(AttributeError, match="handler bug"):
            client.post(PROCESS, {"original": SimpleUploadedFile("sample.m4a", b"synthetic")})
        handler.assert_called_once()


@pytest.mark.parametrize("input_names", [("original", "filepond"), ("original", "original")])
def test_multiple_files_rejected_before_handler(client, user, input_names):
    client.force_login(user)
    files = [SimpleUploadedFile("one.m4a", b"one"), SimpleUploadedFile("two.m4a", b"two")]
    data = {"original": files} if input_names[0] == input_names[1] else dict(zip(input_names, files))
    with patch("testapp.upload_handler") as handler:
        assert client.post(PROCESS, data).status_code == 400
        handler.assert_not_called()
    assert not Upload.objects.exists()
    assert not LocalAudio.objects.exists()


class UploadDatabaseRouter:
    def db_for_write(self, model, **hints):
        if model in (LocalAudio, Upload):
            return "uploads"
        return None


@pytest.mark.django_db(databases=["default", "uploads"])
@pytest.mark.parametrize("fail_registration", [False, True])
def test_creation_uses_linked_write_database(settings, fail_registration):
    settings.DATABASE_ROUTERS = [UploadDatabaseRouter()]
    owner = get_user_model().objects.db_manager("uploads").create_user(username="secondary")
    request = RequestFactory().post(PROCESS, {"original": SimpleUploadedFile("sample.m4a", b"synthetic")})
    request.user = owner
    original_create = QuerySet.create

    def create(queryset, **kwargs):
        if queryset.model is Upload:
            assert queryset.db == "uploads"
            if fail_registration:
                raise IntegrityError("injected registration failure")
        return original_create(queryset, **kwargs)

    with patch.object(QuerySet, "create", autospec=True, side_effect=create) as registration:
        if fail_registration:
            with pytest.raises(IntegrityError, match="injected"):
                UploadCreateView.as_view()(request, app_name="testapp")
        else:
            assert UploadCreateView.as_view()(request, app_name="testapp").status_code == 201
        assert registration.call_count >= 1
    assert not LocalAudio.objects.using("default").exists()
    assert not Upload.objects.using("default").exists()
    assert LocalAudio.objects.using("uploads").count() == (0 if fail_registration else 1)
    assert Upload.objects.using("uploads").count() == (0 if fail_registration else 1)
    if not fail_registration:
        upload = Upload.objects.using("uploads").get()
        assert upload.content_object == LocalAudio.objects.using("uploads").get()


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_default_save_failure_cleans_new_file_and_preserves_error(client, user, cleanup_fails, caplog):
    client.force_login(user)
    storage = InMemoryStorage()
    original_save = Upload.save

    def fail_after_save(instance, *args, **kwargs):
        original_save(instance, *args, **kwargs)
        assert storage.exists(instance.original.name)
        raise IntegrityError("injected model failure")

    original_delete = storage.delete
    deletion = Mock(side_effect=OSError("storage unavailable") if cleanup_fails else original_delete)
    with patch.object(Upload._meta.get_field("original"), "storage", storage):
        with patch.object(Upload, "save", autospec=True, side_effect=fail_after_save) as save:
            with patch.object(storage, "delete", deletion):
                with pytest.raises(IntegrityError, match="injected model failure"):
                    client.post(reverse("filepond:process"), {"original": SimpleUploadedFile("sample.bin", b"new")})
            save.assert_called_once()
            deletion.assert_called_once()
    assert not Upload.objects.exists()
    assert bool(media_files(storage)) == cleanup_fails
    if cleanup_fails:
        assert "Unable to remove upload storage key" in caplog.text


def test_successful_replacement_retains_previous_shared_file(client, user):
    client.force_login(user)
    previous = LocalAudio.objects.create(owner=user, m4a=SimpleUploadedFile("old.m4a", b"old"))
    survivor = LocalAudio.objects.create(owner=user, m4a=previous.m4a.name)
    form_class, context = get_model_form(LocalAudio, upload_field_name="m4a", user_field="owner")
    context["instance"] = previous
    with patch("testapp.upload_handler", return_value=(form_class, context)):
        response = client.post(PROCESS, {"original": SimpleUploadedFile("new.m4a", b"new")})
    assert response.status_code == 201
    previous.refresh_from_db()
    upload = Upload.objects.get(pk=int(response.content))
    assert upload.content_object == previous
    assert upload.original.name == previous.m4a.name != survivor.m4a.name
    assert survivor.m4a.read() == b"old"
    assert previous.m4a.read() == b"new"
