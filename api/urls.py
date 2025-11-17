# urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter

from api.views import (
    LogIngestView,
    ServerLogQueryView,
    LastLogPerSourceView,

    UserViewSet,
    GroupViewSet,
    CircuitViewSet,

    SignUpView,
    SignInView
)

router = SimpleRouter(trailing_slash=False)
router.register(r'user', UserViewSet, basename='user')
router.register(r'group', GroupViewSet, basename='group')
router.register(r'circuit', CircuitViewSet, basename='circuit')

urlpatterns = [

    path('', include(router.urls)),

    path("logs/", ServerLogQueryView.as_view(), name="logs"),
    path("logs-add/", LogIngestView.as_view(), name="logs-add"),
    path("logs-last/", LastLogPerSourceView.as_view(), name="logs-last"),

    path('sign-up', SignUpView.as_view(), name='sign-up'),
    path('sign-in', SignInView.as_view(), name='sign-in'),
]