from django.db import models
from django.contrib.auth.models import User

class Record(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(blank=True, null=True)
    field = models.IntegerField(null=True, blank=True)
    is_leave = models.BooleanField(default=False)