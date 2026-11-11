"""Farm domain serializers."""

from rest_framework import serializers

from apps.farms.models import Farm, FarmMembership, Feeding, Pond


class FarmSerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)

    class Meta:
        model = Farm
        fields = (
            "id",
            "owner_id",
            "name",
            "location",
            "client_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner_id", "created_at", "updated_at")
        validators = []

    def validate(self, attrs):
        client_id = attrs.get("client_id") or getattr(self.instance, "client_id", "")
        owner = getattr(self.instance, "owner", None) or getattr(
            self.context.get("request"), "user", None
        )
        if client_id and owner is not None:
            queryset = Farm.objects.filter(owner=owner, client_id=client_id)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"clientId": "A farm with this client ID already exists."}
                )
        return attrs


class FarmMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = FarmMembership
        fields = ("id", "farm", "user_id", "user_name", "role", "created_at")
        read_only_fields = ("id", "farm", "user_id", "user_name", "created_at")


class PondSerializer(serializers.ModelSerializer):
    farm_id = serializers.PrimaryKeyRelatedField(source="farm", queryset=Farm.objects.all())
    area = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Pond
        fields = (
            "id",
            "farm_id",
            "name",
            "population",
            "length",
            "width",
            "depth",
            "area",
            "species",
            "status",
            "client_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "area", "created_at", "updated_at")
        validators = []

    def validate(self, attrs):
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        client_id = attrs.get("client_id") or getattr(self.instance, "client_id", "")
        if farm and client_id:
            queryset = Pond.objects.filter(farm=farm, client_id=client_id)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"clientId": "A pond with this client ID already exists on this farm."}
                )
        return attrs


class FeedingSerializer(serializers.ModelSerializer):
    pond_id = serializers.PrimaryKeyRelatedField(source="pond", queryset=Pond.objects.all())
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    date = serializers.DateTimeField(source="fed_at", read_only=True)

    class Meta:
        model = Feeding
        fields = (
            "id",
            "pond_id",
            "amount",
            "fed_at",
            "date",
            "note",
            "created_by_id",
            "client_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by_id", "date", "created_at", "updated_at")
        validators = []

    def validate(self, attrs):
        pond = attrs.get("pond") or getattr(self.instance, "pond", None)
        client_id = attrs.get("client_id") or getattr(self.instance, "client_id", "")
        if pond and client_id:
            queryset = Feeding.objects.filter(pond=pond, client_id=client_id)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"clientId": "This feeding record was already imported."}
                )
        return attrs
