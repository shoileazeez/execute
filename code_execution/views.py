from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CodeExecutionSerializer
from .executor import CodeExecutor

class ExecuteCodeView(APIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = CodeExecutor()

    def post(self, request):
        serializer = CodeExecutionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        language = serializer.validated_data['language']
        test_cases = serializer.validated_data['test_cases']
        results = []

        for test_case in test_cases:
            input_data = test_case.get('input_data', {})
            expected_output = test_case.get('expected_output')

            execution_result = self.executor.execute_code(
                code, language, input_data
            )

            if execution_result['status'] == 'success':
                user_output = execution_result['result']
                test_passed = user_output == expected_output

                results.append({
                    'input_data': input_data,
                    'expected_output': expected_output,
                    'user_output': user_output,
                    'status': 'passed' if test_passed else 'failed'
                })
            else:
                results.append({
                    'input_data': input_data,
                    'expected_output': expected_output,
                    'error': execution_result['error'],
                    'status': 'error'
                })

        return Response({'results': results}, status=status.HTTP_200_OK)