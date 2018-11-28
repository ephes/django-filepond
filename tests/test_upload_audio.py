import pytest

from django.urls import reverse

from filepond.models import Upload
from testapp.models import LocalAudio


class TestAudioUpload:
    upload_url = reverse("filepond:process")
    upload_to_testapp_url = reverse("filepond:process", kwargs={"app_name": "testapp"})
    revert_url = reverse("filepond:revert")

    @pytest.mark.django_db
    def test_upload_m4a_audio_with_app(self, client, user, m4a_audio_io):
        # login
        r = client.login(username=user.username, password=user._password)

        # upload
        m4a_audio_io.seek(0)
        r = client.post(self.upload_to_testapp_url, {"filepond": m4a_audio_io})
        upload_pk = int(r.content.decode("utf-8"))

        assert r.status_code == 201
        assert upload_pk > 0

        upload = Upload.objects.get(pk=upload_pk)
        audio = upload.content_object

        assert audio.__class__ == LocalAudio
        assert audio.m4a.path == upload.original.path
