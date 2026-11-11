"""AquaSafe user model and role constants."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager
from apps.common.models import UUIDModel


class UserRole(models.TextChoices):
    FARMER = "Fish Farmer", "Fish Farmer"
    VETERINARY_DOCTOR = "Veterinary Doctor", "Veterinary Doctor"
    SELLER = "Seller / Supplier", "Seller / Supplier"
    ENTHUSIAST = "Enthusiast", "Enthusiast"
    INDIVIDUAL = "Individual", "Individual"
    OTHER = "Other", "Other"
    TECHNICIAN = "Technician", "Technician"
    HARDWARE_INSTALLER = "Hardware Installer", "Hardware Installer"
    ADMINISTRATOR = "Administrator", "Administrator"


class UserLanguage(models.TextChoices):
    ENGLISH = "en", "English"
    HAUSA = "ha", "Hausa"
    YORUBA = "yo", "Yoruba"
    PIDGIN = "pcm", "Nigerian Pidgin"


class User(AbstractBaseUser, PermissionsMixin, UUIDModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=40, blank=True)
    primary_role = models.CharField(
        max_length=40, choices=UserRole.choices, default=UserRole.FARMER
    )
    other_role = models.CharField(max_length=100, blank=True)
    language = models.CharField(
        max_length=5, choices=UserLanguage.choices, default=UserLanguage.ENGLISH
    )
    is_guest = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    EMAIL_FIELD = "email"

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["primary_role"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return self.name

    def get_short_name(self) -> str:
        return self.name.split(" ")[0] if self.name else self.email
