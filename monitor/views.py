from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
import json

from .models import SensorReading, MonitoredUnit, UNIT_TYPE_CHOICES
from .services import build_summary, get_readings, UNIT_THRESHOLDS
from .forms import CustomUserCreationForm


def _build_alert_message(unit_type):
    thresholds = UNIT_THRESHOLDS.get(unit_type, UNIT_THRESHOLDS["fridge"])
    parts = [f"temp outside {thresholds['temp_min']}–{thresholds['temp_max']}°C"]
    if thresholds["humidity_min"] is not None:
        parts.append(f"humidity outside {thresholds['humidity_min']}–{thresholds['humidity_max']}%")
    if thresholds["lux_max"] is not None:
        parts.append(f"light > {thresholds['lux_max']} lux")
    return "Warning: Latest reading is UNSAFE (" + ", ".join(parts) + ")."


def user_register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
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
@user_passes_test(lambda user: user.is_staff)
def management_view(request):
    units = MonitoredUnit.objects.all().order_by("unit_type", "unit_number")
    context = {
        "page_title": "Management",
        "db_count": SensorReading.objects.count(),
        "units": units,
        "unit_type_choices": UNIT_TYPE_CHOICES,
    }
    return render(request, "monitor/management.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff)
def add_unit_view(request):
    if request.method == "POST":
        unit_type = request.POST.get("unit_type")
        existing = MonitoredUnit.objects.filter(unit_type=unit_type).order_by("-unit_number").first()
        unit_number = (existing.unit_number + 1) if existing else 1
        datasette_table = f"{unit_type}_{unit_number}"
        MonitoredUnit.objects.create(
            unit_type=unit_type,
            unit_number=unit_number,
            datasette_table=datasette_table,
        )
    return redirect("monitor:management")


@login_required
@user_passes_test(lambda user: user.is_staff)
def toggle_unit_view(request, unit_id):
    if request.method == "POST":
        unit = MonitoredUnit.objects.get(pk=unit_id)
        unit.active = not unit.active
        unit.save()
    return redirect("monitor:management")


@login_required
def dashboard_data_view(request):
    selected_source = request.GET.get("source", "all")
    dataset = get_readings(
        selected_source=selected_source,
        sort_order="desc",
        door_filter="all",
        limit=120,
    )
    readings = dataset["readings"]
    summary = build_summary(readings)

    if selected_source == "all":
        unit_type = "fridge"
    else:
        unit_type = selected_source.rsplit("_", maxsplit=1)[0]

    alert_message = _build_alert_message(unit_type)

    recent = []
    for r in readings[:12]:
        recent.append({
            "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(r["timestamp"], "strftime") else str(r["timestamp"]),
            "fridge_type": r["fridge_type"],
            "fridge_number": r["fridge_number"],
            "temperature_c": round(r["temperature_c"], 2),
            "humidity_pct": round(r["humidity_pct"], 2),
            "pressure_hpa": round(r["pressure_hpa"], 2),
            "door_status": r["door_status"],
            "light_lux": round(r["light_lux"], 2),
            "safety_status": r.get("safety_status") or "",
        })

    return JsonResponse({
        "latest_temp": round(summary["latest"]["temperature_c"], 2) if summary["latest"] else None,
        "latest_humidity": round(summary["latest"]["humidity_pct"], 2) if summary["latest"] else None,
        "latest_pressure": round(summary["latest"]["pressure_hpa"], 2) if summary["latest"] else None,
        "latest_light": round(summary["latest"]["light_lux"], 2) if summary["latest"] else None,
        "avg_temp": round(summary["avg_temp"], 2) if summary["avg_temp"] is not None else None,
        "avg_humidity": round(summary["avg_humidity"], 2) if summary["avg_humidity"] is not None else None,
        "avg_pressure": round(summary["avg_pressure"], 2) if summary["avg_pressure"] is not None else None,
        "open_events": summary["open_events"],
        "latest_status": summary["latest_status"],
        "alert_message": alert_message,
        "recent_readings": recent,
    })


@login_required
def chart_data_view(request):
    selected_source = request.GET.get("source", "all")
    since = timezone.now() - timedelta(hours=24)

    qs = SensorReading.objects.filter(timestamp__gte=since).order_by("timestamp")

    if selected_source != "all":
        fridge_type, fridge_number = selected_source.rsplit("_", maxsplit=1)
        qs = qs.filter(fridge_type=fridge_type, fridge_number=int(fridge_number))

    units = {}
    for r in qs.values("timestamp", "temperature_c", "humidity_pct", "pressure_hpa", "fridge_type", "fridge_number"):
        key = f"{r['fridge_type'].replace('_', ' ').title()} {r['fridge_number']}"
        if key not in units:
            units[key] = {"labels": [], "temperature": [], "humidity": [], "pressure": []}
        units[key]["labels"].append(r["timestamp"].strftime("%H:%M"))
        units[key]["temperature"].append(round(r["temperature_c"], 2))
        units[key]["humidity"].append(round(r["humidity_pct"], 2))
        units[key]["pressure"].append(round(r["pressure_hpa"], 2))

    return JsonResponse({"units": units})