import os

from django.contrib.contenttypes.models import ContentType

from .models import Upload


def storage_walk_paths(storage, cur_dir=""):
    dirs, files = storage.listdir(cur_dir)
    for directory in dirs:
        new_dir = os.path.join(cur_dir, directory)
        for path in storage_walk_paths(storage, cur_dir=new_dir):
            yield path
    for fname in files:
        path = os.path.join(cur_dir, fname)
        yield path


def get_upload_for_model(instance):
    ct = ContentType.objects.get_for_model(instance)
    return Upload.objects.get(content_type=ct, object_id=instance.pk)
