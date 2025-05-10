from django.urls import path
from .views import (
    LoginView, RegisterView,
    StationListView, StationDetailView,
    SessionListView, SessionDetailView, EndSessionView,
    RateSettingsListView, RateSettingsDetailView, CurrentRatesView,
    RevenueReportView, UsageReportView,
    UserListView, UserDetailView
)

app_name = 'ps'

urlpatterns = [
    # Routes d'authentification
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    
    # Routes de gestion des stations
    path('stations/', StationListView.as_view(), name='station-list'),
    path('stations/<uuid:station_id>/', StationDetailView.as_view(), name='station-detail'),
    
    # Routes de gestion des sessions
    path('sessions/', SessionListView.as_view(), name='session-list'),
    path('sessions/<uuid:session_id>/', SessionDetailView.as_view(), name='session-detail'),
    path('sessions/<uuid:session_id>/end/', EndSessionView.as_view(), name='session-end'),
    
    # Routes de gestion des tarifs
    path('rates/', RateSettingsListView.as_view(), name='rate-list'),
    path('rates/<uuid:rate_id>/', RateSettingsDetailView.as_view(), name='rate-detail'),
    path('rates/current/', CurrentRatesView.as_view(), name='current-rates'),
    
    # Routes de rapports financiers
    path('reports/revenue/', RevenueReportView.as_view(), name='revenue-report'),
    path('reports/usage/', UsageReportView.as_view(), name='usage-report'),
    
    # Routes d'administration des utilisateurs
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),
]
