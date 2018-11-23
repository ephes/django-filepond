import io
import pytest

from .factories import UserFactory


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
