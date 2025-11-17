from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from django.contrib.auth.hashers import make_password

# This is best practice for importing the User model (instead of the line above). It imports the user model dynamically using the AUTH_USER_MODEL setting.
# from django.contrib.auth import get_user_model
# User = get_user_model()

# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    # Add full_name field for easy API display (READ-ONLY)
    # This uses the model's get_full_name() method implicitly or explicitly via a method field.
    full_name = serializers.SerializerMethodField()

    # # Define password explicitly as write-only for security and input control
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_active",
            "created_at",
            "password",
        )
        # Add read_only_fields for fields that shouldn't be modifiable via standard input
        read_only_fields = ["id", "full_name", "created_at"]
        # extra_kwargs = {"password": {"write_only": True, "required": True}}

    def get_full_name(self, obj):
        # Uses the method defined in your User model
        return obj.get_full_name()

    # Create method (for POST/Registration)
    # Todo: Remove the following commented create method later.
    # def create(self, validated_data):
    #     # Explicitly pop the required arguments for clarity and to prevent ambiguity
    #     email = validated_data.pop("email")
    #     password = validated_data.pop("password")
    #     # Ensure password is included in validated_data for create_user to work
    #     user = User.objects.create_user(email, password, **validated_data)
    #     return user
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    # Update method (for PUT/PATCH requests)

    # //* AI suggested this code which was not optimized because it made two database calls when password needed to be updated.
    # def update(self, instance, validated_data):
    #     """
    #     Custom update method to safely handle password hashing during PUT/PATCH.
    #     """
    #     # 1. Safely retrieve the password and remove it from the data
    #     password = validated_data.pop("password", None)

    #     # 2. Update all non-password fields (e.g., first_name, is_staff)
    #     instance = super().update(instance, validated_data)

    #     # 3. Hash and set the new password only if it was provided
    #     if password:
    #         instance.set_password(password)
    #         instance.save()

    #     return instance

    # Option 1:
    def update(self, instance, validated_data):
        # 1. Safely retrieve the password and remove it from the data
        raw_password = validated_data.pop("password", None)

        # 2. If a password was provided, hash it using make_password()
        #    and put the HASHED value back into validated_data.
        if raw_password:
            validated_data["password"] = make_password(raw_password)

        # 3. Call the parent's update method. It sees "password" in validated_data
        #    and correctly saves the HASHED string, along with all other fields,
        #    in a single database call.
        instance = super().update(instance, validated_data)

        return instance

    # Option 2:
    # def update(self, instance, validated_data):
    #     # 1. Safely retrieve the password and remove it from the data
    #     password = validated_data.pop("password", None)

    #     # 2. Hash the password if provided and assign it to the instance,
    #     #    but DO NOT save the instance yet.
    #     if password:
    #         instance.set_password(password)

    #     # 3. Use the parent's update method to apply all remaining fields
    #     #    (first_name, last_name, etc.) AND perform the SINGLE database save.
    #     instance = super().update(instance, validated_data)

    #     return instance


class UserSerializerWithToken(UserSerializer):
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_active",
            "created_at",
            "password",
            "token",
        )

    def get_token(self, obj):
        token = RefreshToken.for_user(obj)
        return str(token.access_token)
