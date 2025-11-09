from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

# Assuming UserSerializer is imported from your serializers file
from .serializers import UserSerializer, UserSerializerWithToken
from rest_framework import status  # For custom error messages
from django.contrib.auth.hashers import make_password  # To hash passwords securely
from .models import User

# Define the view for the profile endpoint
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])  # Ensures only logged-in users can access
# def getUserProfile(request):
#     # request.user is automatically set to the authenticated user from the JWT
#     user = request.user

#     # Serialize the single user object
#     serializer = UserSerializer(user, many=False)

#     return Response(serializer.data)


# @api_view(["PUT"])
# @permission_classes([IsAuthenticated])
# def updateUserProfile(request):
# user = request.user
# serializer = UserSerializerWithToken(user, many=False)

# data = request.data
# user.first_name = data["name"]
# user.username = data["email"]
# user.email = data["email"]

# if data["password"] != "":
#     user.password = make_password(data["password"])

# user.save()

# return Response(serializer.data)


@api_view(["GET"])
@permission_classes(
    [IsAdminUser]
)  # <--- Restricts access to only admin (is_staff=True) users
def getUsers(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(["POST"])  # Restrict this view to only POST requests
def registerUser(request):
    data = request.data
    try:
        # 1. Create the user object
        user = User.objects.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            password=make_password(
                data["password"]
            ),  # 2. Hash the password before creation
        )

        # 3. Serialize and return the user with their token
        serializer = UserSerializerWithToken(user, many=False)

        # Successful creation returns a 200 OK (default DRF behavior)
        return Response(serializer.data)

    except:
        # 4. Define a custom error message for duplicate email/username
        message = {"detail": "User with this email already exists."}

        # 5. Return the error message with a 400 Bad Request status code
        return Response(message, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def getUserById(request, pk):
    user = User.objects.get(id=pk)
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)


# @api_view(["PUT"])
# @permission_classes([IsAdminUser])
# def updateUser(request, pk):
#     user = User.objects.get(id=pk)

#     data = request.data

#     user.first_name = data["name"]
#     user.username = data["email"]
#     user.email = data["email"]
#     user.is_staff = data["isAdmin"]

#     user.save()

#     serializer = UserSerializer(user, many=False)

#     return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def deleteUser(request, pk):
    userForDeletion = User.objects.get(id=pk)
    userForDeletion.delete()
    return Response("User was deleted")
