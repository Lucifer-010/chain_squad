import json
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from Monitor_app.models import Contract, Transaction, AbiItem

class Command(BaseCommand):
    help = 'Loads contract and transaction data from a JSON file into the database.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the data.json file.')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        self.stdout.write(f"Loading data from {json_file_path}...")

        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Clear existing data to avoid duplicates on re-runs
        self.stdout.write("Clearing existing data...")
        Transaction.objects.all().delete()
        AbiItem.objects.all().delete()
        Contract.objects.all().delete()

        # Create Contract
        contract_data = {key: value for key, value in data.items() if key not in ['abi', 'transactions']}
        
        # Extract some top-level info from ABI if available
        name = next((item['outputs'][0]['value'] for item in data.get('abi', []) if item.get('name') == 'name'), None)
        symbol = next((item['outputs'][0]['value'] for item in data.get('abi', []) if item.get('name') == 'symbol'), None)
        
        contract, created = Contract.objects.update_or_create(
            address=contract_data['address'],
            defaults={
                'bytecode': contract_data.get('bytecode'),
                'is_contract': contract_data.get('is_contract', False),
                'creator': contract_data.get('creator'),
                'creation_tx': contract_data.get('creation_tx'),
                'balance_eth': Decimal(str(contract_data.get('balance_eth', 0))),
                'name': name,
                'symbol': symbol,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Successfully created contract {contract.address}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated contract {contract.address}"))

        # Create ABI Items
        abi_items_to_create = []
        for item in data.get('abi', []):
            abi_items_to_create.append(AbiItem(
                contract=contract,
                type=item.get('type', 'unknown'),
                name=item.get('name'),
                constant=item.get('constant'),
                payable=item.get('payable'),
                state_mutability=item.get('stateMutability'),
                inputs=item.get('inputs', []),
                outputs=item.get('outputs', []),
                anonymous=item.get('anonymous')
            ))
        AbiItem.objects.bulk_create(abi_items_to_create)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(abi_items_to_create)} ABI items."))

        # Create Transactions
        transactions_to_create = []
        for tx_data in data.get('transactions', []):
            # Skip if hash is missing
            if not tx_data.get('hash'):
                continue

            transactions_to_create.append(Transaction(
                hash=tx_data['hash'],
                contract=contract,
                block_number=int(tx_data['blockNumber']),
                block_hash=tx_data['blockHash'],
                timestamp=datetime.fromtimestamp(int(tx_data['timeStamp'])),
                nonce=int(tx_data['nonce']),
                transaction_index=int(tx_data['transactionIndex']),
                from_address=tx_data['from'],
                to_address=tx_data.get('to'),
                value=Decimal(tx_data['value']),
                gas=int(tx_data['gas']),
                gas_price=int(tx_data['gasPrice']),
                gas_used=int(tx_data['gasUsed']),
                cumulative_gas_used=int(tx_data['cumulativeGasUsed']),
                input_data=tx_data.get('input', ''),
                method_id=tx_data.get('methodId'),
                function_name=tx_data.get('functionName'),
                tx_receipt_status=tx_data.get('txreceipt_status', ''),
                is_error=bool(int(tx_data.get('isError', 0))),
                confirmations=int(tx_data['confirmations'])
            ))

        Transaction.objects.bulk_create(transactions_to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(transactions_to_create)} transactions."))
        self.stdout.write(self.style.SUCCESS("Data loading complete."))