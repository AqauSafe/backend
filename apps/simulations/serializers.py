"""Simulation request and response serializers."""

from rest_framework import serializers

from apps.farms.models import Pond
from apps.simulations.models import Simulation, SimulationRun
from apps.simulations.services import calculate_simulation


class SimulationRunInputSerializer(serializers.Serializer):
    pond_id = serializers.PrimaryKeyRelatedField(source="pond", queryset=Pond.objects.all())
    duration_days = serializers.IntegerField(min_value=1, max_value=365)
    starting_weight_g = serializers.FloatField(min_value=0.01, max_value=10000)
    daily_growth_g = serializers.FloatField(min_value=0, max_value=100)
    daily_feed_kg = serializers.FloatField(min_value=0, max_value=1000)
    daily_mortality_percent = serializers.FloatField(min_value=0, max_value=100)
    temperature_c = serializers.FloatField(min_value=-5, max_value=50)
    dissolved_oxygen_mg_l = serializers.FloatField(min_value=0, max_value=30)
    ph = serializers.FloatField(min_value=0, max_value=14)

    def create(self, validated_data):
        pond = validated_data.pop("pond")
        population = pond.population
        result = calculate_simulation(population=population, **validated_data)
        return SimulationRun.objects.create(
            farm=pond.farm,
            pond=pond,
            created_by=self.context["request"].user,
            population=population,
            metadata={"clientRequest": True},
            **validated_data,
            **result,
        )


class SimulationRunSerializer(serializers.ModelSerializer):
    farm_id = serializers.UUIDField(read_only=True)
    pond_id = serializers.UUIDField(read_only=True)
    population = serializers.IntegerField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    starting_weight_g = serializers.FloatField(read_only=True)
    daily_growth_g = serializers.FloatField(read_only=True)
    daily_feed_kg = serializers.FloatField(read_only=True)
    daily_mortality_percent = serializers.FloatField(read_only=True)
    temperature_c = serializers.FloatField(read_only=True)
    dissolved_oxygen_mg_l = serializers.FloatField(read_only=True)
    ph = serializers.FloatField(read_only=True)
    projected_biomass_kg = serializers.FloatField(read_only=True)
    total_feed_kg = serializers.FloatField(read_only=True)
    estimated_fcr = serializers.FloatField(read_only=True)

    class Meta:
        model = SimulationRun
        fields = (
            "id",
            "farm_id",
            "pond_id",
            "created_at",
            "formula_version",
            "population",
            "duration_days",
            "starting_weight_g",
            "daily_growth_g",
            "daily_feed_kg",
            "daily_mortality_percent",
            "temperature_c",
            "dissolved_oxygen_mg_l",
            "ph",
            "projected_survivors",
            "projected_biomass_kg",
            "total_feed_kg",
            "estimated_fcr",
            "warnings",
            "daily_projection",
        )


class SimulationStateInputSerializer(serializers.Serializer):
    pond_id = serializers.PrimaryKeyRelatedField(source="pond", queryset=Pond.objects.all())
    temperature = serializers.FloatField(min_value=-5, max_value=50, required=False)
    oxygen = serializers.FloatField(min_value=0, max_value=30, required=False)
    ph = serializers.FloatField(min_value=0, max_value=14, required=False)
    level = serializers.FloatField(min_value=0, max_value=100, required=False)
    turbidity_ntu = serializers.FloatField(min_value=0, max_value=1000, required=False)
    recorded_at = serializers.DateTimeField(required=False)
    client_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    message_id = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate(self, attrs):
        if not any(
            attrs.get(field) is not None
            for field in ("temperature", "oxygen", "ph", "level", "turbidity_ntu")
        ):
            raise serializers.ValidationError(
                "At least one of temperature, oxygen, pH, level or turbidity is required."
            )
        return attrs


class SimulationSerializer(serializers.ModelSerializer):
    farm_id = serializers.UUIDField(read_only=True)
    pond_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Simulation
        fields = (
            "id",
            "farm_id",
            "pond_id",
            "is_active",
            "state",
            "last_state_at",
            "created_at",
            "updated_at",
        )
