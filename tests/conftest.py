import os
import io
import pytest

from django.conf import settings
from django.core.files.storage import default_storage

from .factories import UserFactory
from filepond.utils import storage_walk_paths


@pytest.fixture(scope='session', autouse=True)
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
