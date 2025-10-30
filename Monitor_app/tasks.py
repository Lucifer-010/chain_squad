# tasks.py
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

import requests
from web3 import Web3
from web3.exceptions import TransactionNotFound

# --- Configuration ---
# It is recommended to use a specific RPC for your Arbitrum Orbit chain.
#RPC_URL = "https://nova.arbitrum.io/rpc"   Default RPC URL

# --- Health Alert Thresholds ---
CRITICAL_BALANCE_ETH = 1.0  # Alert if sequencer balance drops below this.
BLOCK_PRODUCTION_THRESHOLD_SECONDS = 300  # 5 minutes. Alert if no new blocks are produced.

# --- Analytics Parameters ---
NUM_BLOCKS_FOR_AVERAGES = 20 # Number of recent blocks to analyze for historical stats.
MIN_TRANSACTIONS_TO_FETCH = 20 # The minimum number of recent transactions to retrieve details for.
MAX_BLOCKS_TO_SCAN_FOR_TXS = 50 # Safety limit to prevent scanning too far back for transactions.


# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Helper Functions ---

def to_serializable(obj):
    """Helper function to convert complex types to JSON serializable formats."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, 'hex'): # Handles HexBytes
        return obj.hex()
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)

def get_transaction_details(w3: Web3, tx_hash) -> dict:
    """Fetches and processes a single transaction to extract key details and its receipt."""
    try:
        tx = w3.eth.get_transaction(tx_hash)
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        
        status = receipt.get("status")
        gas_used = int(receipt.get("gasUsed", 0))
        effective_gas_price = int(receipt.get("effectiveGasPrice", tx.get("gasPrice", 0)))
        tx_fee_wei = gas_used * effective_gas_price

        tx_type = "Simple Transfer"
        if tx.to is None:
            tx_type = "Contract Creation"
        # A simple heuristic: if there's input data beyond the basic '0x', it's likely a contract call.
        elif tx.input and len(tx.input) > 2:
            tx_type = "Contract Call"
        
        return {
            "hash": tx.hash.hex(),
            "block_number": tx.blockNumber,
            "from": tx["from"],
            "to": tx.get("to"),
            "value_eth": float(w3.from_wei(tx.value, "ether")),
            "status": "success" if status == 1 else "failed",
            "gas_used": gas_used,
            "gas_price_gwei": float(w3.from_wei(effective_gas_price, "gwei")),
            "transaction_fee_eth": float(w3.from_wei(tx_fee_wei, "ether")),
            "type": tx_type,
        }
    except TransactionNotFound:
        logging.warning(f"Receipt for tx {tx_hash.hex()} not found, skipping.")
        return None
    except Exception as e:
        logging.error(f"Error processing tx {tx_hash.hex()}: {e}")
        return None


def get_l3_vital_health(rpc_url: str):
    """
    Fetches and analyzes a rich set of health and performance metrics for an L3 chain,
    structured for analytics and graphing.

    This function connects to a chain's RPC endpoint and gathers data on:
    - Core chain and node information.
    - Sequencer balance and health.
    - Detailed analytics of the latest block.
    - Expanded historical performance metrics (e.g., min/max tx counts, gas usage).
    - At least 20 of the most recent transactions, scanning multiple blocks if needed.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60.0}))
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC endpoint: {rpc_url}")
    except Exception as e:
        logging.error(f"RPC connection error: {e}")
        return {"error": f"RPC connection error: {e}"}

    data = {"timestamp_utc": datetime.now(timezone.utc), "health_alerts": []}
    now = datetime.now(timezone.utc)

    # --- 1. Fetch Latest Block ---
    try:
        latest_block = w3.eth.get_block("latest")
    except Exception as e:
        logging.error(f"Could not fetch the latest block: {e}")
        return {"error": "Could not fetch the latest block."}

    # --- 2. Core Chain & Node Information ---
    data["chain_info"] = {
        "rpc_url": rpc_url,
        "chain_id": int(w3.eth.chain_id),
        "client_version": w3.client_version,
    }

    # --- 3. Node Health & Sync Status ---
    try:
        sync_status = w3.eth.syncing
        if sync_status:
            current = sync_status.get("currentBlock", 0)
            highest = sync_status.get("highestBlock", 1)
            progress = (current / highest * 100) if highest > 0 else 0
            data["node_health"] = {
                "syncing": True,
                "sync_progress_percent": f"{progress:.2f}",
                "sync_current_block": current,
                "sync_highest_block": highest,
            }
            data["health_alerts"].append(f"Node is syncing: {progress:.2f}% complete.")
        else:
            data["node_health"] = {"syncing": False}
    except Exception as e:
        data["node_health"] = {"syncing": "N/A"}
        logging.warning(f"Could not fetch syncing status: {e}")
    
    try:
        data["node_health"]["peer_count"] = w3.net.peer_count
    except Exception as e:
        data["node_health"]["peer_count"] = "N/A"
        logging.warning(f"Could not fetch peer count: {e}")

    # --- 4. Latest Block Analytics ---
    block_timestamp = datetime.fromtimestamp(int(latest_block.timestamp), timezone.utc)
    gas_used_percent = (latest_block.gasUsed / latest_block.gasLimit * 100) if latest_block.gasLimit > 0 else 0
    time_since_last_block = (now - block_timestamp).total_seconds()

    if time_since_last_block > BLOCK_PRODUCTION_THRESHOLD_SECONDS:
        data["health_alerts"].append(
            f"No new blocks in over {BLOCK_PRODUCTION_THRESHOLD_SECONDS / 60:.1f} minutes. "
            f"Last block was {time_since_last_block:.0f} seconds ago."
        )

    data["latest_block_analytics"] = {
        "block_number": int(latest_block.number),
        "block_hash": latest_block.hash.hex(),
        "block_timestamp_utc": block_timestamp,
        "time_since_block_seconds": time_since_last_block,
        "transaction_count": len(latest_block.transactions),
        "gas_used": int(latest_block.gasUsed),
        "gas_limit": int(latest_block.gasLimit),
        "gas_used_percentage": f"{gas_used_percent:.2f}",
        "base_fee_per_gas_gwei": float(w3.from_wei(latest_block.get("baseFeePerGas", 0), "gwei")),
        "block_size_bytes": int(latest_block.size),
    }

    # --- 5. Sequencer Information ---
    try:
        sequencer_address = latest_block.get("miner")
        if sequencer_address and w3.is_address(sequencer_address):
            balance_wei = w3.eth.get_balance(sequencer_address)
            balance_eth = float(w3.from_wei(balance_wei, "ether"))
            data["sequencer_info"] = {
                "address": sequencer_address,
                "balance_eth": balance_eth,
                "balance_critical_threshold_eth": CRITICAL_BALANCE_ETH
            }
            if balance_eth < CRITICAL_BALANCE_ETH:
                 data["health_alerts"].append(
                    f"Sequencer ETH balance is critical: {balance_eth:.4f} ETH. "
                    f"Below threshold of {CRITICAL_BALANCE_ETH} ETH."
                )
    except Exception as e:
        logging.warning(f"Could not determine sequencer balance: {e}")
        data["sequencer_info"] = {"address": "Error", "balance_eth": "N/A", "error": str(e)}

    # --- 6. Historical Performance (Averages & Ranges) ---
    try:
        if latest_block.number > NUM_BLOCKS_FOR_AVERAGES:
            # Fetch last N blocks to calculate historical stats
            recent_blocks = [w3.eth.get_block(latest_block.number - i) for i in range(NUM_BLOCKS_FOR_AVERAGES)]
            
            first_block_for_avg = recent_blocks[-1]
            time_diff = latest_block.timestamp - first_block_for_avg.timestamp
            avg_block_time = time_diff / NUM_BLOCKS_FOR_AVERAGES
            
            tx_counts = [len(b.transactions) for b in recent_blocks]
            gas_used_percentages = [(b.gasUsed / b.gasLimit * 100) if b.gasLimit > 0 else 0 for b in recent_blocks]
            block_sizes = [b.size for b in recent_blocks]

            avg_txs_per_block = sum(tx_counts) / len(tx_counts)
            
            data["historical_performance"] = {
                "analysis_block_range": f"{first_block_for_avg.number} - {latest_block.number}",
                "avg_block_time_seconds": f"{avg_block_time:.2f}",
                "avg_txs_per_block": f"{avg_txs_per_block:.2f}",
                "estimated_tps": f"{(avg_txs_per_block / avg_block_time):.2f}" if avg_block_time > 0 else "0.00",
                "avg_gas_used_percentage": f"{sum(gas_used_percentages) / len(gas_used_percentages):.2f}",
                "max_txs_in_block": max(tx_counts),
                "min_txs_in_block": min(tx_counts),
                "max_gas_used_percentage": f"{max(gas_used_percentages):.2f}",
                "min_gas_used_percentage": f"{min(gas_used_percentages):.2f}",
                "max_block_size_bytes": max(block_sizes),
                "min_block_size_bytes": min(block_sizes),
            }
        else:
            data["historical_performance"] = {"error": "Not enough blocks on-chain to calculate historical stats."}
    except Exception as e:
        data["historical_performance"] = {"error": f"Could not calculate historical stats: {e}"}
        logging.warning(f"Could not calculate historical metrics: {e}")

    # --- 7. Fetch 20+ Most Recent Detailed Transactions ---
    detailed_transactions = []
    try:
        current_block_num = latest_block.number
        blocks_scanned = 0
        while len(detailed_transactions) < MIN_TRANSACTIONS_TO_FETCH and blocks_scanned < MAX_BLOCKS_TO_SCAN_FOR_TXS:
            block_to_scan = w3.eth.get_block(current_block_num)
            # Iterate in reverse to get the most recent transactions first
            for tx_hash in reversed(block_to_scan.transactions):
                if len(detailed_transactions) >= MIN_TRANSACTIONS_TO_FETCH:
                    break
                tx_details = get_transaction_details(w3, tx_hash)
                if tx_details:
                    detailed_transactions.append(tx_details)
            
            current_block_num -= 1
            blocks_scanned += 1
            if current_block_num < 0:
                break
        
        data["detailed_transactions"] = detailed_transactions
    except Exception as e:
        data["detailed_transactions"] = {"error": f"Failed to fetch detailed transactions: {e}"}
        logging.error(f"Failed to fetch detailed transactions: {e}")

    # --- 8. Final Health Status ---
    data["overall_status"] = "ALERT" if data["health_alerts"] else "OK"

    return data


