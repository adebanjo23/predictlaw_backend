from django.db import models

class User(models.Model):
    username = models.CharField(max_length=255, null=False, unique=True)
    phone = models.CharField(max_length=22, null=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.username
