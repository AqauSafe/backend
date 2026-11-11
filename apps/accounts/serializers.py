"""Authentication and account serializers."""

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserLanguage, UserRole
from apps.accounts.roles import PUBLIC_REGISTRATION_ROLES, assign_primary_role_group


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="primary_role", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "role",
            "primary_role",
            "other_role",
            "language",
            "is_guest",
            "is_active",
            "is_staff",
            "roles",
            "date_joined",
            "created_at",
        )
        read_only_fields = fields

    def get_roles(self, obj: User) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class AuthDataSerializer(TokenPairSerializer):
    user = UserSerializer(read_only=True)


class AuthResponseSerializer(serializers.Serializer):
    data = AuthDataSerializer(read_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RefreshResponseSerializer(serializers.Serializer):
    data = TokenPairSerializer(read_only=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("name", "phone", "other_role", "language")
        extra_kwargs = {
            "name": {"required": False},
            "phone": {"required": False},
            "other_role": {"required": False},
            "language": {"required": False},
        }


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6, trim_whitespace=False)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    role = serializers.ChoiceField(
        choices=[(role.value, role.label) for role in PUBLIC_REGISTRATION_ROLES]
    )
    other_role = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    language = serializers.ChoiceField(choices=UserLanguage.choices, default=UserLanguage.ENGLISH)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        if attrs["role"] == UserRole.OTHER and not attrs.get("other_role", "").strip():
            raise serializers.ValidationError({"other_role": "Please specify your category."})
        candidate = User(email=attrs["email"], name=attrs["name"])
        validate_password(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.pop("role")
        user = User.objects.create_user(primary_role=role, password=password, **validated_data)
        assign_primary_role_group(user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs["email"].strip().lower()
        user = authenticate(request=request, username=email, password=attrs["password"])
        if user is None:
            raise AuthenticationFailed("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationFailed("This account is inactive.")
        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value: str) -> str:
        try:
            RefreshToken(value)
        except Exception as exc:  # noqa: BLE001
            raise serializers.ValidationError("Invalid or expired refresh token.") from exc
        return value

    def save(self, **kwargs):
        RefreshToken(self.validated_data["refresh"]).blacklist()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=6, trim_whitespace=False)

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        validate_password(value, user=self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user


class AquaSafeTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class AquaSafeTokenRefreshSerializer(TokenRefreshSerializer):
    pass


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "app_label", "model")
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(source="permissions.all", many=True, read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "permissions")
        read_only_fields = fields
