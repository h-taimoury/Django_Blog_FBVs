from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
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


@api_view(["POST"])
@permission_classes([AllowAny])  # Allows unauthenticated access for registration
def registerUser(request):
    # 1. Instantiate the serializer with the request data
    serializer = UserSerializer(data=request.data)

    # 2. Check if the incoming data is VALID
    if serializer.is_valid():
        # 3. If valid, call save(). This executes the serializer's custom create()
        #    method which calls User.objects.create_user() to hash the password securely.
        user = serializer.save()

        # 4. Prepare the success response data
        response_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "message": "User registered successfully.",
        }

        # 5. Return success status (201 CREATED)
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 6. If NOT valid, return the detailed error messages (400 BAD REQUEST)
    # This automatically handles missing fields, invalid emails, and duplicate emails.
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminUser])
def userDetail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # --- 1. GET (Retrieve a single user) ---
    if request.method == "GET":
        serializer = UserSerializer(user)
        return Response(serializer.data)

    # --- 2. PUT (Replace entire user object) ---
    elif request.method == "PUT":
        # data=request.data is the JSON/form data sent by the client
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # --- 3. PATCH (Partially update user object) ---
    elif request.method == "PATCH":
        # 'partial=True' allows you to update only the fields provided in request.data
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # --- 4. DELETE (Remove user object) ---
    elif request.method == "DELETE":
        user.delete()
        # Return a 204 No Content status on successful deletion
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Fallback response for unhandled methods (optional)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
