from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import SensorReading
from .services import build_summary, get_readings


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
        "dashboard_url": "https://dashboard.diffa.co.uk/-/dashboards/fridge-monitor",
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
