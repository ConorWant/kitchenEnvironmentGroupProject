from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import SensorReading, MonitoredUnit, UNIT_TYPE_CHOICES
from .services import build_summary, get_readings, UNIT_THRESHOLDS
from .forms import CustomUserCreationForm


DOOR_OPEN_ALERT_SECONDS = 60


def _get_unit_alerts(latest_reading, unit_type, unit_label, unit_readings=None):
    thresholds = UNIT_THRESHOLDS.get(unit_type, UNIT_THRESHOLDS["fridge"])
    issues = []
    temp = latest_reading["temperature_c"]
    if temp < thresholds["temp_min"]:
        issues.append(f"Temp {temp:.1f}°C below min {thresholds['temp_min']}°C")
    elif temp > thresholds["temp_max"]:
        issues.append(f"Temp {temp:.1f}°C above max {thresholds['temp_max']}°C")
    lux = latest_reading["light_lux"]
    if thresholds["lux_max"] is not None and lux > thresholds["lux_max"]:
        issues.append(f"Light {lux:.0f} lux above max {thresholds['lux_max']} lux")
    humidity = latest_reading["humidity_pct"]
    if thresholds["humidity_min"] is not None and humidity < thresholds["humidity_min"]:
        issues.append(f"Humidity {humidity:.1f}% below min {thresholds['humidity_min']}%")
    elif thresholds["humidity_max"] is not None and humidity > thresholds["humidity_max"]:
        issues.append(f"Humidity {humidity:.1f}% above max {thresholds['humidity_max']}%")
    if str(latest_reading.get("door_status", "")).upper() == "OPEN":
        open_since = latest_reading["timestamp"]
        for r in (unit_readings or []):
            if str(r.get("door_status", "")).upper() == "OPEN":
                open_since = r["timestamp"]
            else:
                break
        if hasattr(open_since, "tzinfo") and open_since.tzinfo is None:
            open_since = timezone.make_aware(open_since)
        elapsed = timezone.now() - open_since
        if elapsed.total_seconds() >= DOOR_OPEN_ALERT_SECONDS:
            minutes = int(elapsed.total_seconds() / 60)
            issues.append(f"Door open for {minutes} min")
    return {"unit": unit_label, "issues": issues} if issues else None


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
    at_minute = request.GET.get("at_minute", "").strip()
    datetime_error = ""

    qs = SensorReading.objects.all()

    if selected_source != "all":
        fridge_type, fridge_number = selected_source.rsplit("_", maxsplit=1)
        qs = qs.filter(fridge_type=fridge_type, fridge_number=int(fridge_number))

    if door_filter != "all":
        qs = qs.filter(door_status__iexact=door_filter)

    target_page = request.GET.get("page")
    if at_minute:
        try:
            target_dt = datetime.fromisoformat(at_minute)
            if timezone.is_naive(target_dt):
                target_dt = timezone.make_aware(target_dt, timezone.get_current_timezone())

            # Jump to the page where this timestamp would appear under current filters/sort.
            if sort_order == "asc":
                before_count = qs.filter(timestamp__lt=target_dt).count()
            else:
                before_count = qs.filter(timestamp__gt=target_dt).count()
            target_page = (before_count // 40) + 1
        except ValueError:
            datetime_error = "Please enter a valid date and time."

    order_by = "timestamp" if sort_order == "asc" else "-timestamp"
    qs = qs.order_by(order_by)

    paginator = Paginator(qs, 40)
    page_obj = paginator.get_page(target_page)

    dataset = get_readings(
        selected_source=selected_source,
        sort_order=sort_order,
        door_filter=door_filter,
        limit=0,
    )

    context = {
        "page_title": "History",
        "dataset": dataset,
        "page_obj": page_obj,
        "selected_source": selected_source,
        "sort_order": sort_order,
        "door_filter": door_filter,
        "at_minute": at_minute,
        "datetime_error": datetime_error,
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

    seen_units = {}
    unit_readings = {}
    for r in readings:
        key = (r["fridge_type"], r["fridge_number"])
        if key not in seen_units:
            seen_units[key] = r
        unit_readings.setdefault(key, []).append(r)

    alerts = []
    for (unit_type, unit_number), latest_r in seen_units.items():
        label = f"{unit_type.replace('_', ' ').title()} {unit_number}"
        alert = _get_unit_alerts(latest_r, unit_type, label, unit_readings[(unit_type, unit_number)])
        if alert:
            alerts.append(alert)

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
        "alerts": alerts,
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