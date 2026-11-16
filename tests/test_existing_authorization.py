from unittest.mock import patch

import pytest
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from filepond.forms import get_model_form
from filepond.models import Upload
from testapp.models import LocalAudio

pytestmark = pytest.mark.django_db
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
