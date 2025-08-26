from decimal import Decimal
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .models import Cycle, Rental, UserProfile, CycleReview
from django.db.models import Avg
from .forms import RegisterForm, LoginForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import RentalRequest
from django.utils import timezone
from django.views.decorators.http import require_POST

def home(request):
    return render(request, 'landingpg.html')

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user_type = form.cleaned_data.get('user_type')
            is_owner = (user_type == 'owner')
            profile = user.userprofile
            profile.is_owner = is_owner
            profile.save()
            login(request, user)
            return redirect('account_setup')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            profile = UserProfile.objects.get(user=user)
            if not profile.details_completed:
                return redirect('account_setup')
            return redirect('owner_dashboard' if profile.is_owner else 'user_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
@csrf_exempt
def account_setup(request):
    profile = UserProfile.objects.get(user=request.user)
    user = request.user

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()

        profile.phone_number = request.POST.get('phone_number')
        profile.details_completed = True
        profile.save()

        if profile.is_owner:
            Cycle.objects.create(
                owner=user,
                name=request.POST.get('name'),
                rate_per_hour=request.POST.get('rate_per_hour'),
                location_lat=request.POST.get('lat'),
                location_lng=request.POST.get('lng'),
                description=request.POST.get('description'),
                image=request.FILES.get('cycle_image'),
                is_available=True
            )

        return redirect('owner_dashboard' if profile.is_owner else 'user_dashboard')

    return render(request, 'account_setup.html', {'profile': profile})

@login_required
def confirm_rental_request(request, request_id):
    rental_request = get_object_or_404(RentalRequest, id=request_id, cycle__owner=request.user)

    if request.method == "POST" and rental_request.is_approved is None and rental_request.cycle.is_available:
        rental_request.is_approved = True
        rental_request.save()

        cycle = rental_request.cycle
        cycle.is_available = False
        cycle.save()

        Rental.objects.create(
            cycle=cycle,
            renter=rental_request.renter,
            start_time=timezone.now(),
            end_time=rental_request.end_time
        )

    return redirect('owner_dashboard')

@csrf_exempt
@login_required
def edit_cycle(request, cycle_id):
    if request.method == 'POST':
        try:
            cycle = Cycle.objects.get(id=cycle_id, owner=request.user)
            data = json.loads(request.body)
            cycle.description = data.get('description', cycle.description)
            cycle.is_available = data.get('is_available', cycle.is_available)

            if 'latitude' in data and 'longitude' in data:
                cycle.latitude = data['latitude']
                cycle.longitude = data['longitude']

            cycle.save()
            return JsonResponse({'status': 'success'})
        except Cycle.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Cycle not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)

@csrf_exempt
@login_required
def remove_listing(request, cycle_id):
    if request.method == 'POST':
        try:
            cycle = Cycle.objects.get(id=cycle_id, owner=request.user)
            cycle.is_available = False
            cycle.save()
            return JsonResponse({'success': True})
        except Cycle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cycle not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)

@csrf_exempt
@login_required
def relist_cycle(request, cycle_id):
    if request.method == 'POST':
        try:
            cycle = Cycle.objects.get(id=cycle_id, owner=request.user)
            cycle.is_available = True
            cycle.save()
            return JsonResponse({'success': True})
        except Cycle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cycle not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)

from django.db.models import Avg
from .models import Cycle, RentalRequest, Rental

from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Cycle, RentalRequest
import json

@csrf_exempt  
@require_POST
@login_required
def submit_booking(request):
    try:
        data = json.loads(request.body)

        cycle_id = data.get("cycle_id")
        message = data.get("message")
        end_time_str = data.get("end_time")
        phone = data.get("phone")

        end_time = parse_datetime(end_time_str)
        if not end_time:
            return JsonResponse({"error": "Invalid end time format"}, status=400)

        user = request.user
        try:
            cycle = Cycle.objects.get(id=cycle_id)
        except Cycle.DoesNotExist:
            return JsonResponse({"error": "Cycle not found"}, status=404)

        RentalRequest.objects.create(
            cycle=cycle,
            renter=user,
            message=message,
            contact_number=phone,
            end_time=end_time,
        )

        return JsonResponse({"status": "success"})
    
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def owner_dashboard(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)
    if not profile.is_owner:
        return redirect('user_dashboard')

    cycle = Cycle.objects.filter(owner=user).first()

    reviews = []
    avg_rating = 0
    latest_reviews = []
    current_renter = None
    return_time = None
    contact_number = None
    start_time = None
    rental_requests = []

    if cycle:
        reviews = cycle.reviews.all().order_by('-timestamp')
        avg_rating = reviews.aggregate(avg=Avg('stars'))['avg'] or 0
        avg_rating = round(avg_rating, 1)
        latest_reviews = reviews[:3]

        active_rental = Rental.objects.filter(cycle=cycle, is_active=True).first()
        if active_rental:
            current_renter = active_rental.renter
            return_time = active_rental.end_time
            try:
                rental_request = RentalRequest.objects.filter(
                    cycle=cycle,
                    renter=current_renter,
                    is_approved=True
                ).order_by('-id').first()

                start_time = active_rental.start_time 
                contact_number = rental_request.contact_number
            except RentalRequest.DoesNotExist:
                return_time = None
                contact_number = None

        rental_requests = RentalRequest.objects.filter(cycle=cycle, is_approved=None)

    context = {
        'cycle': cycle,
        'avg_rating': avg_rating,
        'latest_reviews': latest_reviews,
        'current_renter': current_renter,
        'return_time': return_time,
        'start_time': start_time,
        'contact_number': contact_number,
        'rental_requests': rental_requests,
    }

    return render(request, 'owner_dashboard.html', context)

@login_required
def confirm_return(request, cycle_id):
    cycle = get_object_or_404(Cycle, id=cycle_id, owner=request.user)
    
    if request.method == "POST":
        rental = Rental.objects.filter(cycle=cycle, is_active=True).first()
        
        if rental:
            rental.is_active = False
            rental.save()

            cycle.is_available = True
            cycle.save()

    return redirect('owner_dashboard')

def user_dashboard(request):
    cycles = Cycle.objects.filter(is_available=True)

    cycle_data = [
        {
            'name': cycle.name,
            'rate_per_hour': float(cycle.rate_per_hour),
            'location_lat': cycle.location_lat,
            'location_lng': cycle.location_lng
        }
        for cycle in cycles if cycle.location_lat and cycle.location_lng
    ]

    # Check if user has an active rental
    active_rental = None
    if request.user.is_authenticated:
        active_rental = Rental.objects.filter(renter=request.user, is_active=True).select_related('cycle').first()

    context = {
        'cycles': cycles,
        'cycle_data_json': json.dumps(cycle_data),
        'active_rental': active_rental,
    }
    return render(request, 'user_dashboard.html', context)

@csrf_exempt
def get_cycle_locations(request):
    cycles = Cycle.objects.filter(is_available=True)
    data = [
        {
            'name': cycle.name,
            'lat': cycle.location_lat,
            'lng': cycle.location_lng,
            'owner': cycle.owner.username
        }
        for cycle in cycles
    ]
    return JsonResponse({'cycles': data})

def about_page(request):
    return render(request, 'about.html')

def contact_page(request):
    return render(request, 'contact.html')

def logout_view(request):
    logout(request)
    return redirect('home')
