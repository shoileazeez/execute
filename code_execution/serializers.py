from rest_framework import serializers

class TestCaseSerializer(serializers.Serializer):
    input_data = serializers.JSONField(required=False, default=dict)
    expected_output = serializers.JSONField(required=True)

class CodeExecutionSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    language = serializers.ChoiceField(
        choices=['python', 'javascript', 'java', 'cpp'],
        required=True
    )
    test_cases = TestCaseSerializer(many=True, required=True)