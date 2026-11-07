import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from .factories import UserFactory


@pytest.fixture(autouse=True)
def isolated_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture()
def default_password():
    return "password"


@pytest.fixture()
def user(default_password):
    user = UserFactory(password=default_password)
    user._password = default_password
    return user


@pytest.fixture()
def user2(default_password):
    user = UserFactory(password=default_password)
    user._password = default_password
    return user


def create_small_rgb():
    # this is a small test jpeg
    from PIL import Image

    img = Image.new("RGB", (200, 200), (255, 0, 0, 0))
    return img


@pytest.fixture()
def small_jpeg_io():
    rgb = create_small_rgb()
    im_io = io.BytesIO()
    rgb.save(im_io, format="JPEG", quality=60, optimize=True, progressive=True)
    im_io.seek(0)
    im_io.name = "testimage.jpg"
    return im_io


def synthetic_m4a():
    # Uploads are stored verbatim; no codec or real recording is needed.
    return b"synthetic audio payload"


@pytest.fixture()
def m4a_audio_django_file():
    m4a = synthetic_m4a()
    simple_m4a = SimpleUploadedFile(name="test.m4a", content=m4a, content_type="audio/mp4")
    return simple_m4a


@pytest.fixture()
def m4a_audio_io():
    m4a = synthetic_m4a()
    audio_io = io.BytesIO(m4a)
    audio_io.seek(0)
    audio_io.name = "testaudio.m4a"
    return audio_io
