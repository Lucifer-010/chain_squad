from rest_framework import serializers
from .models import Contract, Transaction, AbiItem

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        exclude = ['contract'] # Exclude contract to avoid circular dependency in nested view

class AbiItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbiItem
        exclude = ['contract']

class ContractSerializer(serializers.ModelSerializer):
    """
    Serializer for a single contract, without transactions.
    """
    class Meta:
        model = Contract
        fields = '__all__'

class ContractDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a contract including its transactions and ABI.
    This is great for an analytical deep-dive into one contract.
    """
    transactions = TransactionSerializer(many=True, read_only=True)
    abi = AbiItemSerializer(many=True, read_only=True)

    class Meta:
        model = Contract
        fields = [
            'address', 'creator', 'creation_tx', 'balance_eth', 'is_contract',
            'name', 'symbol', 'total_supply', 'decimals',
            'transactions', 'abi'
        ]