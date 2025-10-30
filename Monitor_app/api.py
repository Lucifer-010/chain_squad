from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from .models import Contract, Transaction
from .serializers import (RPCMonitorSerializer,
    UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer
)
import requests
from .serializers import RPCMonitorSerializer
from .tasks import get_l3_vital_health, to_serializable
import json

@api_view(['POST'])
def get_chain_health_analytics(request):
    """
    API endpoint to fetch health and analytics data for a given L3 chain RPC URL.

    Accepts a POST request with a JSON body containing the 'rpc_url'.
    Example:
    {
        "rpc_url": "https://nova.arbitrum.io/rpc"
    }
    """
    # 1. Validate the incoming request data
    serializer = RPCMonitorSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    rpc_url = serializer.validated_data['rpc_url']

    try:
        # 2. Execute the monitoring logic
        analytics_data = get_l3_vital_health(rpc_url)

        # 3. Check for errors from the monitoring function
        if 'error' in analytics_data:
            # Return a server-side error if the script failed to connect or fetch data
            return Response(analytics_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # 4. Serialize the data to ensure consistent JSON formatting
        # The to_serializable helper handles complex types like datetime and HexBytes
        response_data = json.loads(json.dumps(analytics_data, default=to_serializable))

        # 5. Return the successful response
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        # Catch any other unexpected errors during execution
        return Response(
            {"error": "An unexpected server error occurred.", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class RegisterAPIView(APIView):
    """
    API endpoint for user registration.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Optionally, log in the user immediately after registration
            # For JWT, you'd typically return tokens here.
            # Using CustomTokenObtainPairSerializer to get tokens
            token_serializer = CustomTokenObtainPairSerializer(data={
                'username': user.username,
                'password': request.data['password']
            })
            token_serializer.is_valid(raise_exception=True)
            return Response({
                "user": UserSerializer(user).data,
                "message": "User registered successfully.",
                **token_serializer.validated_data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserAPIView(APIView):
    """
    API endpoint to retrieve the current authenticated user's details.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)




@api_view(['POST'])
def send_telegram_alert_view(request):
    """
    Receives bot_token, chat_id, and message from the frontend
    and forwards the alert to the Telegram API.
    """
    bot_token = request.data.get('bot_token')
    chat_id = request.data.get('chat_id')
    message = request.data.get('message')

    if not all([bot_token, chat_id, message]):
        return Response(
            {"error": "Missing bot_token, chat_id, or message"},
            status=status.HTTP_400_BAD_REQUEST
        )

    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(send_url, json=payload, timeout=15)
        response.raise_for_status()
        return Response({"success": True, "response": response.json()}, status=status.HTTP_200_OK)
    except requests.exceptions.RequestException as e:
        return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

