from django.db import models
from django.urls import reverse

from django.contrib.auth import get_user_model

from model_utils.models import TimeStampedModel


class LocalImage(TimeStampedModel):
    """
    Receive test images via filepond.
    """

    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    image = models.ImageField(upload_to="testapp/images")

    def __str__(self):
        return f"{self.pk} {self.image.name}"
