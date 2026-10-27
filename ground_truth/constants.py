"""Pinned inputs. Changing any of these changes every published number."""

RPC_URL = "https://base-rpc.publicnode.com"
# Keyless nodes that take 50-call batches (checked 2026-10-27). They serve only lookups whose empty answer is an
# error (by hash, block number or nonce); eth_getLogs, where a short answer would pass unnoticed, stays on RPC_URL.
RPC_POOL = (RPC_URL, "https://base-mainnet.public.blastapi.io")  # 1rpc.io/base dropped: free usage cap hit mid-census
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
X402SCAN_COMMIT = "5732bb83c8c4290f413f24318a838e3fee4ed2bf"

TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOPIC_AUTHORIZATION_USED = "0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5"
# Proxy and batch-settlement events, from x402-foundation/x402 contracts/evm/src at commit dbe1080a.
TOPIC_PROXY_SETTLED = "0x97088ec3606cfe8cc112180570d03fcde05f9b8e1bfef8e27784eaf5dd5691b6"  # Settled()
TOPIC_PROXY_SETTLED_PERMIT = "0xde5b89d10fc800c459329c382fabfcad0be0ed7e5328e01fae04e507b09ef5d8"  # SettledWithPermit()
TOPIC_BATCH_CLAIMED = "0x36bd546bb573e8921fdbfd934bbed62d872796b01792cd240cce27f79dd3eddd"
TOPIC_BATCH_DEPOSITED = "0x6c2a09353b5e75e70d0b9778b80a413809bb235d46c211811c474b3346791d89"
TOPIC_BATCH_SETTLED = "0x7337b4386b690fdb8ba66905b92b9d45d33bc6626ee2620c905fb150ec0cc47d"
TOPIC_BATCH_CHANNEL_CREATED = "0x69d8248d5566bdb2ebc4d218970710d8378a2ff9b709a999e052b71970f808fa"
X402_CONTRACTS_COMMIT = "dbe1080ac7f65e2e05cc8430a834c255a6800828"

# Deployed x402 Permit2 proxies on Base (x402-foundation/x402 contracts/evm/README.md).
PROXIES = {
    "exact_proxy": "0x402085c248eea27d92e8b30b2c58ed07f9e20001",
    "upto": "0x4020a4f3b7b90cca423b9fabcc0ce57c6c240002",
    "batch_settlement": "0x4020074e9df2ce1dee5a9c1b5c3f541d02a10003",
}
BATCH_CONTRACT = PROXIES["batch_settlement"]

DUST_ATOMIC = 10_000  # $0.01 at 6 decimals
SECOND_HOP_SHARE = 0.9  # a transfer out of an address that just received at least this share of it is a forward
