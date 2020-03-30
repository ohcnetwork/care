from rest_framework import serializers


class ModelHistorySerializer(serializers.ModelSerializer):
    def __init__(self, model, *args, **kwargs):
        self.Meta.model = model
        super().__init__()

    class Meta:
        fields = "__all__"
