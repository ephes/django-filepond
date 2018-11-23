import pytest

from django.urls import reverse

from filepond.models import Upload


class TestImageUpload:
    upload_url = reverse("filepond:process")
    revert_url = reverse("filepond:revert")

    @pytest.mark.django_db
    def test_upload_image_not_authenticated(self, client, small_jpeg_io):
        small_jpeg_io.seek(0)
        r = client.post(self.upload_url, {"filepond": small_jpeg_io})
        # redirect to login
        assert r.status_code == 302

    @pytest.mark.django_db
    def test_upload_image_authenticated(self, client, user, small_jpeg_io):
        # login
        r = client.login(username=user.username, password=user._password)

        # upload
        small_jpeg_io.seek(0)
        r = client.post(self.upload_url, {"filepond": small_jpeg_io})

        assert r.status_code == 201
        assert int(r.content.decode("utf-8")) > 0

    @pytest.mark.django_db
    def test_revert_image_upload_wrong_user(self, client, user, user2, small_jpeg_io):
        assert user.pk != user2.pk
        # login
        r = client.login(username=user.username, password=user._password)

        # upload
        small_jpeg_io.seek(0)
        r = client.post(self.upload_url, {"filepond": small_jpeg_io})
        assert r.status_code == 201

        # revert with wrong user
        image_pk = int(r.content.decode("utf-8"))
        assert Upload.objects.filter(pk=image_pk).count() == 1

        client.logout()
        r = client.login(username=user2.username, password=user2._password)

        r = client.post(self.revert_url, str(image_pk), content_type="application/json")
        assert r.status_code == 200
        assert Upload.objects.filter(pk=image_pk).count() == 1

    @pytest.mark.django_db
    def test_revert_image_upload(self, client, user, small_jpeg_io):
        # login
        r = client.login(username=user.username, password=user._password)

        # upload
        small_jpeg_io.seek(0)
        r = client.post(self.upload_url, {"filepond": small_jpeg_io})
        assert r.status_code == 201

        # revert
        image_pk = int(r.content.decode("utf-8"))
        assert Upload.objects.filter(pk=image_pk).count() == 1

        r = client.post(self.revert_url, str(image_pk), content_type="application/json")
        assert r.status_code == 200
        assert Upload.objects.filter(pk=image_pk).count() == 0
