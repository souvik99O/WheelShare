from django.contrib import admin
from .models import UserProfile, Cycle, Rental, UserReview, CycleReview, RentalRequest

admin.site.register(UserProfile)
admin.site.register(Cycle)
admin.site.register(Rental)
admin.site.register(RentalRequest)
admin.site.register(UserReview)
admin.site.register(CycleReview)
