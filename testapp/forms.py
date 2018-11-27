from django import forms

from .models import TestImage


class TestImageForm(forms.ModelForm):
    upload_attr_name = "image"

    class Meta:
        model = TestImage
        fields = ["image"]
