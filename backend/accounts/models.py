from django.db import models
from django.conf import settings

# Create your models here.
class Profile(models.Model):
    user=models.OneToOneField(
        settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='profile'
    )
    phone=models.CharField(max_length=10,blank=True)
    photo=models.ImageField(upload_to='profile_photos/',blank=True)


    def is_complete(self):
        return bool(self.photo and self.phone and self.user.email)
    
    def __str__(self):
        return self.user.username