from rest_framework import serializers


# ---------------------------------- Air Search ----------------------------------
class AirSearchSegmentSerializer(serializers.Serializer):
    origin = serializers.CharField()
    destination = serializers.CharField()
    departure_date = serializers.DateField()


class AirSearchSerializer(serializers.Serializer):
    adult_quantity = serializers.IntegerField()
    child_quantity = serializers.IntegerField()
    child_age = serializers.IntegerField()
    infant_quantity = serializers.IntegerField()
    user_ip = serializers.IPAddressField()
    journey_type = serializers.CharField()  # 1.Oneway 2.Return 3.Multicity
    booking_class = (
        serializers.CharField()
    )  # 1.Economy 2.Premium Economy 3.Business 4.First

    segments = serializers.ListField(child=AirSearchSegmentSerializer())


# ---------------------------------- Air Rules ----------------------------------
class AirRulesSerializer(serializers.Serializer):
    api_name = serializers.CharField()
    search_id = serializers.CharField()
    result_id = serializers.CharField()
