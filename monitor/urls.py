from django.urls import path
from . import views

app_name = "monitor"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("history/", views.history_view, name="history"),
    path("management/", views.management_view, name="management"),
    path("management/add-unit/", views.add_unit_view, name="add_unit"),
    path("management/toggle-unit/<int:unit_id>/", views.toggle_unit_view, name="toggle_unit"),
    path("register/", views.user_register_view, name="register"),
    path('verify-email/<int:uid>/<str:token>/', views.verify_email, name='verify_email'),
    path("dashboard-data/", views.dashboard_data_view, name="dashboard_data"),
    path("chart-data/", views.chart_data_view, name="chart_data"),
]