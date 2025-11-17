from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    # TokenRefreshView,
)
from .views import (
    # userProfile,
    getUsers,
    userDetail,
    registerUser,
    userProfile,
)

urlpatterns = [
    path("", getUsers, name="users"),
    path("register/", registerUser, name="register"),
    path("me/", userProfile, name="me"),
    # The following two lines are for Simple JWT library
    path("login/", TokenObtainPairView.as_view(), name="login"),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("<int:pk>/", userDetail, name="user-detail"),
]
