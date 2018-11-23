from django.db import models
from django.urls import reverse
from django.conf import settings

from django.contrib.auth import get_user_model

from model_utils.models import TimeStampedModel


class Upload(TimeStampedModel):
    """
    Hold uploaded files.
    """

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    original = models.FileField()

    @property
    def original_url(self):
        return reverse("filepond:get", kwargs={"pk": self.pk, "size": "original"})

    def __str__(self):
        return f"{self.pk} {self.original.name}"
