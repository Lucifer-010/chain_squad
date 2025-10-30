from django.db import models

class Contract(models.Model):
    """
    Represents an Ethereum smart contract.
    """
    address = models.CharField(max_length=42, primary_key=True)
    bytecode = models.TextField(null=True, blank=True)
    is_contract = models.BooleanField(default=True)
    creator = models.CharField(max_length=42, null=True, blank=True)
    creation_tx = models.CharField(max_length=66, null=True, blank=True, unique=True)
    balance_eth = models.DecimalField(max_digits=30, decimal_places=18, default=0.0)

    # Fields that can be populated from ABI calls
    name = models.CharField(max_length=255, null=True, blank=True)
    symbol = models.CharField(max_length=255, null=True, blank=True)
    total_supply = models.DecimalField(max_digits=40, decimal_places=0, null=True, blank=True)
    decimals = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name or self.address

class Transaction(models.Model):
    """
    Represents a transaction related to a smart contract.
    """
    hash = models.CharField(max_length=66, primary_key=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='transactions')
    block_number = models.BigIntegerField()
    block_hash = models.CharField(max_length=66)
    timestamp = models.DateTimeField()
    nonce = models.IntegerField()
    transaction_index = models.IntegerField()
    from_address = models.CharField(max_length=42)
    to_address = models.CharField(max_length=42, null=True, blank=True)
    value = models.DecimalField(max_digits=30, decimal_places=0)
    gas = models.BigIntegerField()
    gas_price = models.BigIntegerField()
    gas_used = models.BigIntegerField()
    cumulative_gas_used = models.BigIntegerField()
    input_data = models.TextField()
    method_id = models.CharField(max_length=10, null=True, blank=True)
    function_name = models.CharField(max_length=255, null=True, blank=True)
    tx_receipt_status = models.CharField(max_length=1) # '1' for success, '0' for failure
    is_error = models.BooleanField()
    confirmations = models.BigIntegerField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return self.hash

class AbiItem(models.Model):
    """
    Represents a single item in a contract's ABI.
    """
    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='abi')
    
    # Common fields
    type = models.CharField(max_length=50) # 'function', 'constructor', 'event', 'fallback'
    name = models.CharField(max_length=255, null=True, blank=True)
    constant = models.BooleanField(null=True)
    payable = models.BooleanField(null=True)
    state_mutability = models.CharField(max_length=50, null=True, blank=True)
    
    # For inputs/outputs
    inputs = models.JSONField(default=list)
    outputs = models.JSONField(default=list)

    # For events
    anonymous = models.BooleanField(null=True)

    class Meta:
        verbose_name = "ABI Item"
        verbose_name_plural = "ABI Items"

    def __str__(self):
        if self.name:
            return f"{self.type}: {self.name}"
        return f"Unnamed {self.type}"