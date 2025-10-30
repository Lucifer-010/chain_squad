# tasks.py
from web3 import Web3
import json
from datetime import datetime, timezone
from decimal import Decimal
import math
import requests
import logging

# --- Configuration ---
# You can adjust these settings
# Using a more specific RPC for an Arbitrum Orbit chain is recommended
# For this example, we'll continue with a public Arbitrum RPC
RPC_URL = "https://nova.arbitrum.io/rpc"
CRITICAL_BALANCE_ETH = 1.0  # Alert if sequencer balance drops below this
BLOCK_PRODUCTION_THRESHOLD_SECONDS = 300 # 5 minutes


# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from hexbytes import HexBytes
except ImportError:
    HexBytes = None


def to_serializable(obj):
    """Helper function to convert complex types to JSON serializable formats."""
    if isinstance(obj, Decimal):
        return float(obj)
    if HexBytes and isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)

def send_telegram_alert(bot_token: str, chat_id: str, message: str):
    """
    Sends an alert message to a specified Telegram chat.
    """
    if not bot_token or not chat_id:
        logging.warning("Telegram Bot Token or Chat ID is not configured. Skipping notification.")
        return {"success": False, "error": "Bot Token or Chat ID not provided."}

    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(send_url, json=payload, timeout=5)
        response.raise_for_status()
        return {"success": True, "response": response.json()}
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Telegram alert: {e}")
        return {"success": False, "error": str(e)}

def get_l3_vital_health(rpc_url: str):
    """
    Fetches and analyzes vital health metrics for an L3 chain.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        error_msg = f"Failed to connect to RPC {rpc_url}"
        logging.error(error_msg)
        return {"error": error_msg}

    data = {"rpc_url": rpc_url, "health_alerts": []}
    now = datetime.now(timezone.utc)

    # 1. L3's current block height (to show it's "live")
    try:
        latest_block = w3.eth.get_block("latest")
        data["latest_block_number"] = int(latest_block.number)
        ts = int(latest_block.timestamp)
        latest_ts = datetime.fromtimestamp(ts, timezone.utc)
        data["block_timestamp"] = latest_ts.isoformat()
        
        # Health Check: Time since last block
        time_since_last_block = (now - latest_ts).total_seconds()
        if time_since_last_block > BLOCK_PRODUCTION_THRESHOLD_SECONDS:
            data["health_alerts"].append(
                f"No new blocks in over {BLOCK_PRODUCTION_THRESHOLD_SECONDS / 60:.1f} minutes. Last block was {time_since_last_block:.0f} seconds ago."
            )

    except Exception as e:
        logging.error(f"Could not fetch the latest block: {e}")
        return {"error": "Could not fetch the latest block."}

    # Get client version
    try:
        data["client_version"] = w3.client_version
    except Exception as e:
        data["client_version"] = "N/A"
        logging.warning(f"Could not fetch client version: {e}")

    # 2. The ETH balance of the L3's "Sequencer"
    try:
        # Heuristic: The 'miner' of recent blocks is often the sequencer.
        sequencer_address = latest_block.get("miner")
        if sequencer_address and w3.is_address(sequencer_address):
            balance_wei = w3.eth.get_balance(sequencer_address)
            balance_eth = float(w3.from_wei(balance_wei, "ether"))
            data["sequencer_address"] = sequencer_address
            data["sequencer_balance_eth"] = balance_eth
            
            # Health Check: Sequencer balance critical point
            if balance_eth < CRITICAL_BALANCE_ETH:
                 data["health_alerts"].append(
                    f"Sequencer ETH balance is critical: {balance_eth:.4f} ETH. Below threshold of {CRITICAL_BALANCE_ETH} ETH."
                )
        else:
            data["sequencer_address"] = "Unknown"
            data["sequencer_balance_eth"] = "N/A"
    except Exception as e:
        data["sequencer_address"] = "Error"
        data["sequencer_balance_eth"] = "N/A"
        logging.warning(f"Could not determine sequencer balance: {e}")

    # 3. The timestamp of the last batch posted (to show it's "settling")
    try:
        # This is a placeholder as it's highly specific to the rollup implementation.
        # For Arbitrum, this info is not available via a standard public RPC.
        # One would typically query the L2 (parent chain) for transactions from the batch poster address.
        data["last_batch_posted_timestamp"] = "N/A (Requires L2 indexing or specific RPC)"
    except Exception as e:
        data["last_batch_posted_timestamp"] = "N/A"

    # 4. All major vital health metrics
    data["chain_id"] = int(w3.eth.chain_id)
    data["gas_limit"] = getattr(latest_block, "gasLimit", "N/A")
    data["gas_used"] = getattr(latest_block, "gasUsed", "N/A")
    data["block_hash"] = getattr(latest_block, "hash", b'').hex()
    data["transaction_count"] = len(getattr(latest_block, "transactions", []))
    
    try:
        gas_price_wei = int(w3.eth.gas_price)
        data["network_gas_price_gwei"] = float(w3.from_wei(gas_price_wei, "gwei"))
    except Exception:
        data["network_gas_price_gwei"] = "N/A"

    # Get peer count
    try:
        data["peer_count"] = w3.net.peer_count
    except Exception as e:
        data["peer_count"] = "N/A"
        logging.warning(f"Could not fetch peer count: {e}")

    # 5. The 15 recent transactions
    transactions = []
    try:
        block_txs = latest_block.get("transactions", [])
        for tx_hash in reversed(block_txs[-15:]):
            tx = w3.eth.get_transaction(tx_hash)
            transactions.append({
                "hash": tx.hash.hex(),
                "from": tx["from"],
                "to": tx["to"],
                "value_eth": float(w3.from_wei(tx.value, "ether")),
                "gas": tx.gas,
            })
        data["recent_transactions"] = transactions
    except Exception as e:
        data["recent_transactions"] = []
        logging.warning(f"Could not fetch recent transactions: {e}")


    # 6. Chain size (estimation)
    # Direct chain size from RPC is not possible.
    # This is a conceptual metric, often measured by the node's database size on disk.
    data["chain_size_on_disk"] = "N/A (Requires access to the node's filesystem)"


    # 7. Gas fee limit, spent gas fee, balance, and balance critical point
    data["gas_fee_metrics"] = {
        "gas_limit_per_block": data["gas_limit"],
        "gas_spent_latest_block": data["gas_used"],
        "sequencer_balance": data.get("sequencer_balance_eth", "N/A"),
        "sequencer_balance_critical_point": CRITICAL_BALANCE_ETH
    }


    # Final summary of health status
    if not data["health_alerts"]:
        data["overall_status"] = "OK"
    else:
        data["overall_status"] = "ALERT"

    return data


if __name__ == "__main__":
    logging.info(f"Fetching vital health metrics for L3 at {RPC_URL}")
    
    analytics_data = get_l3_vital_health(RPC_URL)

    # Save to disk
    with open("l3_health_data.json", "w") as f:
        json.dump(analytics_data, f, indent=4, default=to_serializable)
    
    print(json.dumps(analytics_data, indent=4, default=to_serializable))

    # Example of how to use the alert system
    if analytics_data.get("overall_status") == "ALERT":
        logging.warning("L3 health check detected the following problems:")
        for alert in analytics_data.get("health_alerts", []):
            logging.warning(f"- {alert}")