from django.contrib.auth import get_user_model
from django.db import models
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


class BigAudio(models.Model):
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    original = models.FileField(upload_to="testapp/big")


class TextAudio(models.Model):
    id = models.CharField(primary_key=True, max_length=40)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    original = models.FileField(upload_to="testapp/text")


class ChildAudio(LocalAudio):
    """Multi-table inheritance child whose primary key is the parent link."""

    title = models.CharField(max_length=40, blank=True)


class ProfileAudio(models.Model):
    """One-to-one primary key referencing the integer user key."""

    owner = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, primary_key=True)
    original = models.FileField(upload_to="testapp/profile")
