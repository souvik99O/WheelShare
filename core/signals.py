from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Rental, Cycle

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.userprofile.save()

@receiver(post_save, sender=Rental)
def update_cycle_availability(sender, instance, created, **kwargs):
    cycle = instance.cycle
    if created and instance.is_active and cycle.is_available:
        cycle.is_available = False
        cycle.save()

