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
)

urlpatterns = [
    path("", getUsers, name="users"),
    # path("me/", userProfile, name="user-profile"),
    path("register/", registerUser, name="register"),
    # The following two lines are for Simple JWT library
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("<str:pk>/", userDetail, name="user-detail"),
]
