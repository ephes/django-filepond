from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


from model_utils.models import TimeStampedModel


class Upload(TimeStampedModel):
    """
    Hold uploaded files and a generic relation to the model
    that has beed registered for this upload.
    """

    # request.user and uploaded file
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    original = models.FileField(upload_to="uploads")

    # generic foreign key
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    @property
    def original_url(self):
        return reverse("filepond:get", kwargs={"pk": self.pk, "size": "original"})

    def __str__(self):
        return f"{self.pk} {self.original.name}"
