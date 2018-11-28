import os
import io
import pytest

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from .factories import UserFactory
from filepond.utils import storage_walk_paths


@pytest.fixture(scope="session", autouse=True)
def media_dir_cleanup():
    # Will be executed before the first test
    # and collects all paths in media root, that already
    # existed before running the tests
    print("media root: ", settings.MEDIA_ROOT)
    existing_paths = set(storage_walk_paths(default_storage))
    yield existing_paths
    # Will be executed after the last test
    # and finds all paths in media root which were added
    # during the tests and remove them
    for path in storage_walk_paths(default_storage):
        if path not in existing_paths:
            abs_path = os.path.join(settings.MEDIA_ROOT, path)
            os.unlink(abs_path)


@pytest.fixture()
def fixture_dir():
    curdir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(curdir, "fixtures")


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


def read_test_m4a(fixture_dir):
    with open(os.path.join(fixture_dir, "test.m4a"), "rb") as f:
        m4a = f.read()
    return m4a


@pytest.fixture()
def m4a_audio_django_file(fixture_dir):
    m4a = read_test_m4a(fixture_dir)
    simple_m4a = SimpleUploadedFile(
        name="test.m4a", content=m4a, content_type="audio/mp4"
    )
    return simple_m4a


@pytest.fixture()
def m4a_audio_io(fixture_dir):
    m4a = read_test_m4a(fixture_dir)
    audio_io = io.BytesIO(m4a)
    audio_io.seek(0)
    audio_io.name = "testaudio.m4a"
    return audio_io
