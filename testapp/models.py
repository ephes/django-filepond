from django.db import models
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


class LocalAudio(TimeStampedModel):
    """
    Receive test audio tracks via filepond.
    """

    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    m4a = models.FileField(upload_to="testapp/audio", blank=True, null=True)
    mp3 = models.FileField(upload_to="testapp/audio", blank=True, null=True)

    def __str__(self):
        return f"audio: {self.pk}"
