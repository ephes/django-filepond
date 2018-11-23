import factory

from django.contrib.auth import get_user_model


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: "user-{0}".format(n))
    email = factory.Sequence(lambda n: "user-{0}@example.com".format(n))
    # setting default password to "password", but you can also pass different ones
    password = factory.PostGenerationMethodCall("set_password", "password")

    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)
