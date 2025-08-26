from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_owner = models.BooleanField(default=False) 
    details_completed = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username

class Cycle(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cycles')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='cycle_images/', blank=True, null=True)
    rate_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    location_lat = models.FloatField()
    location_lng = models.FloatField()
    is_available = models.BooleanField(default=True)
    average_rating = models.FloatField(default=0)

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

class Rental(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rentals')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    return_requested = models.BooleanField(default=False)

    def initiate_return(self):
        self.return_requested = True
        self.save()

    def mark_completed(self):
        self.is_active = False
        self.end_time = timezone.now()
        self.save()
        self.cycle.is_available = True
        self.cycle.save()

    def __str__(self):
        return f"{self.cycle.name} rented by {self.renter.username}"

class RentalRequest(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    renter = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    contact_number = models.CharField(max_length=15)
    requested_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(null=True)  

class UserReview(models.Model):
    rental = models.OneToOneField(Rental, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_user_reviews')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_user_reviews')
    stars = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.reviewee.username}"

class CycleReview(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE)
    stars = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.cycle.name} by {self.reviewer.username}"
