from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Contract, Transaction
from .serializers import ContractSerializer, ContractDetailSerializer, TransactionSerializer
from . import tasks

class ContractViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows contracts to be viewed.
    
    - The 'list' action provides a summary of all contracts.
    - The 'retrieve' action provides detailed data for a single contract.
    - The 'analyze' action allows for on-the-fly analysis of a contract address.
    """
    queryset = Contract.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Default permissions

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        For the 'analyze_contract' action, we allow any user.
        For all other actions, we use the default permissions defined in `permission_classes`.
        """
        if self.action == 'analyze_contract':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ContractDetailSerializer
        return ContractSerializer

    @action(detail=False, methods=['post'], url_path='analyze')
    def analyze_contract(self, request):
        """
        Analyzes a contract address provided in the POST request body.
        It fetches the contract data, saves it to the database, and returns
        the serialized contract details.
        """
        contract_address = request.data.get('address')
        if not contract_address:
            return Response(
                {"error": "Contract address is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            contract_instance = tasks.load_contract_data_from_address(contract_address)
            serializer = ContractDetailSerializer(contract_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='send-telegram-alert', permission_classes=[permissions.AllowAny])
    def send_telegram_alert(self, request):
        """
        Sends a Telegram alert.
        Expects 'bot_token', 'chat_id', and 'message' in the POST data.
        """
        bot_token = request.data.get('bot_token')
        chat_id = request.data.get('chat_id')
        message = request.data.get('message')

        if not all([bot_token, chat_id, message]):
            return Response(
                {"error": "bot_token, chat_id, and message are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = tasks.send_telegram_alert(bot_token, chat_id, message)

        if result.get("success"):
            return Response({"message": "Telegram alert sent successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": f"Failed to send Telegram alert: {result.get('error')}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)