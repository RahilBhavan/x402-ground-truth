# x402 ground truth

How much of the x402 payment volume on Base survives named, rerunnable exclusion rules. **Status: planning and slice 1.** No published results yet.

- Plan: [docs/prd.md](docs/prd.md) (DRAFT, red-teamed once: [review/](review/))
- Sources: [research/sources.md](research/sources.md)
- Slice 1 result (one hour, keyless): [docs/slices/s1.md](docs/slices/s1.md)

```sh
python3 -m ground_truth capture --days 7   # x402scan's rolling Base figure, saved with its timestamp
python3 -m ground_truth hour               # one hour of Base blocks via a keyless public RPC
python3 -m unittest discover -s tests
```

Python 3.12 standard library only. Public onchain data only.
