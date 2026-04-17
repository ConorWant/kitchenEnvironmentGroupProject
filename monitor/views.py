from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse

from .models import SensorReading
from .services import build_summary, get_readings
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm

def user_register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate account until it is confirmed
            user.save()
            token = default_token_generator.make_token(user)
            uid = user.pk
            verification_link = request.build_absolute_uri(
                reverse('monitor:verify_email', args=[uid, token])
            )
            send_mail(
                'Verify your email',
                f'Click the link to verify your email: {verification_link}',
                'noreply@yourdomain.com',
                [user.email],
                fail_silently=False,
            )
            return render(
                request,
                "registration/register_success.html",
                {
                    "page_title": "Registration Successful",
                    "email": user.email,
                },
            )
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})
    
def verify_email(request, uid, token):
    try:
        user = User.objects.get(pk=uid)
    except User.DoesNotExist:
        return HttpResponse('Invalid user')

    if default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse('Email verified! You can now log in.')
    else:
        return HttpResponse('Invalid or expired token')    


@login_required
def dashboard_view(request):
    selected_source = request.GET.get("source", "all")

    dataset = get_readings(
        selected_source=selected_source,
        sort_order="desc",
        door_filter="all",
        limit=120,
    )
    readings = dataset["readings"]
    summary = build_summary(readings)

    context = {
        "page_title": "Dashboard",
        "dataset": dataset,
        "summary": summary,
        "selected_source": selected_source,
        "recent_readings": readings[:12],
    }
    return render(request, "monitor/dashboard.html", context)


@login_required
def history_view(request):
    selected_source = request.GET.get("source", "all")
    sort_order = request.GET.get("sort", "desc")
    door_filter = request.GET.get("door", "all")

    dataset = get_readings(
        selected_source=selected_source,
        sort_order=sort_order,
        door_filter=door_filter,
        limit=None,
    )

    paginator = Paginator(dataset["readings"], 40)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_title": "History",
        "dataset": dataset,
        "page_obj": page_obj,
        "selected_source": selected_source,
        "sort_order": sort_order,
        "door_filter": door_filter,
    }
    return render(request, "monitor/history.html", context)


@login_required
@user_passes_test(lambda user: user.is_superuser)
def live_dashboard_view(request):
    context = {
        "page_title": "Live Dashboard",
        "dashboard_url": "https://dashboard.pilsworth.org/-/dashboards/fridge-monitor",
    }
    return render(request, "monitor/live_dashboard.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff)
def management_view(request):
    sources = (
        SensorReading.objects.values("fridge_type", "fridge_number")
        .distinct()
        .order_by("fridge_type", "fridge_number")
    )

    context = {
        "page_title": "Management",
        "db_count": SensorReading.objects.count(),
        "sources": sources,
    }
    return render(request, "monitor/management.html", context)


   # from .services import is_anomalous

# def dashboard_view(request):
#     readings = SensorReading.objects.all()
#     for reading in readings:
#         reading.anomalous = is_anomalous(reading)
#     return render(request, "dashboard.html", {"readings": readings})
