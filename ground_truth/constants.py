"""Pinned inputs. Changing any of these changes every published number."""

RPC_URL = "https://base-rpc.publicnode.com"
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
X402SCAN_COMMIT = "5732bb83c8c4290f413f24318a838e3fee4ed2bf"

TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOPIC_AUTHORIZATION_USED = "0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5"
TOPIC_SETTLED = "0x97088ec3" # prefix only; full topic resolved in slice 2

# Deployed x402 Permit2 proxies on Base (x402-foundation/x402 contracts/evm/README.md).
PROXIES = {
    "exact_proxy": "0x402085c248eea27d92e8b30b2c58ed07f9e20001",
    "upto": "0x4020a4f3b7b90cca423b9fabcc0ce57c6c240002",
    "batch_settlement": "0x4020074e9df2ce1dee5a9c1b5c3f541d02a10003",
}

DUST_ATOMIC = 10_000  # $0.01 at 6 decimals
