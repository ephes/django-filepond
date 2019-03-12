from django import forms

from .models import Upload


class UploadForm(forms.ModelForm):
    class Meta:
        model = Upload
        fields = ["original"]


def get_model_form(
    upload_model, upload_field_name="original", upload_fields=None, user_field=None
):
    """Convenience function to Create an upload form."""
    if upload_fields is None:
        upload_fields = []
    if upload_field_name not in upload_fields:
        upload_fields.append(upload_field_name)

    class DynamicUploadForm(forms.ModelForm):
        class Meta:
            model = upload_model
            fields = upload_fields

    context = {"user_field": user_field, "upload_field_name": upload_field_name}
    return DynamicUploadForm, context
