"""Authentication, profile and RBAC views."""

from django.contrib.auth.models import Group, Permission
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    AuthResponseSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PermissionSerializer,
    RefreshRequestSerializer,
    RefreshResponseSerializer,
    RegisterSerializer,
    RoleSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.audit.services import log_event


def token_payload(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def auth_response(user: User) -> dict:
    return {"user": UserSerializer(user).data, **token_payload(user)}


class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_scope = "register"

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_event(
            actor=user,
            action="user.registered",
            entity_type="user",
            entity_id=str(user.id),
            request=request,
        )
        return Response({"data": auth_response(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        log_event(
            actor=user,
            action="user.logged_in",
            entity_type="user",
            entity_id=str(user.id),
            request=request,
        )
        return Response({"data": auth_response(user)})


class RefreshView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=RefreshRequestSerializer, responses={200: RefreshResponseSerializer})
    def post(self, request):
        refresh = request.data.get("refresh") or request.COOKIES.get("aquasafe_refresh")
        if not refresh:
            return Response(
                {"error": {"code": "refresh_required", "message": "A refresh token is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            serializer = TokenRefreshSerializer(data={"refresh": refresh})
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response(
                {
                    "error": {
                        "code": "invalid_refresh",
                        "message": "Invalid or expired refresh token.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response({"data": serializer.validated_data})


class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        refresh = request.data.get("refresh") or request.COOKIES.get("aquasafe_refresh")
        serializer = LogoutSerializer(data={"refresh": refresh})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("aquasafe_refresh")
        return response


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "password"

    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_event(
            actor=request.user,
            action="user.password_changed",
            entity_type="user",
            entity_id=str(request.user.id),
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all().prefetch_related("groups")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    search_fields = ["email", "name", "phone"]
    ordering_fields = ["date_joined", "name", "email"]
    filterset_fields = ["primary_role", "is_active"]


class RoleListView(generics.ListAPIView):
    queryset = Group.objects.all().prefetch_related("permissions__content_type")
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None


class PermissionListView(generics.ListAPIView):
    queryset = Permission.objects.select_related("content_type").all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser]
    search_fields = ["codename", "name"]
    ordering_fields = ["codename", "name"]
    filterset_fields = ["content_type__app_label"]
