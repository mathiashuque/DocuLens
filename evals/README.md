# Evaluations

Run the deterministic baseline from the repository root:

```sh
python -m evals.run_baselines --output evals/results/baseline-v1.json
python -m evals.run_baselines --output evals/results/baseline-v1.json --check
```

The command uses only checked-in synthetic fixtures, fake embeddings, and recorded
grounded-QA outputs. It makes no network or provider calls. See
[`docs/evaluation.md`](../docs/evaluation.md) for measured values and limitations.
