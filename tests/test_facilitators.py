import unittest

from ground_truth.facilitators import parse_base

SRC = """
  addresses: {
    [Network.SOLANA]: [
      { address: '2wKupLR9q6wXYppw8Gr2NvWxKBUqm4PPJKkQfoxHDBg4', tokens: [USDC_SOLANA_TOKEN] },
    ],
    [Network.BASE]: [
      {
        address: '0xC6699d2aada6c36dfea5c248dd70f9cb0235cb63',
        tokens: [USDC_BASE_TOKEN],
      },
      {
        address: '0x25659315106580ce2a787ceec5efb2d347b539c9',
        deprecated: true,
        tokens: [USDC_BASE_TOKEN],
      },
    ],
  },
"""


class SyncedByX402scan(unittest.TestCase):
    def test_a_deprecated_facilitator_or_address_is_not_synced(self):
        from ground_truth.facilitators import parse_facilitator
        live = "export const f = { id: 'x', " + SRC + " };"
        dead = "export const f = { id: 'x', deprecated: true, " + SRC + " };"
        self.assertEqual([a["x402scan_synced"] for a in parse_facilitator(live)], [True, False])
        self.assertEqual([a["x402scan_synced"] for a in parse_facilitator(dead)], [False, False])


class ParseBase(unittest.TestCase):
    def test_reads_only_base_addresses_lowercased_with_deprecated_flag(self):
        self.assertEqual(parse_base(SRC), [
            {"address": "0xc6699d2aada6c36dfea5c248dd70f9cb0235cb63", "deprecated": False},
            {"address": "0x25659315106580ce2a787ceec5efb2d347b539c9", "deprecated": True},
        ])

    def test_file_without_base_block_gives_nothing(self):
        self.assertEqual(parse_base("addresses: { [Network.SOLANA]: [] }"), [])


if __name__ == "__main__":
    unittest.main()
