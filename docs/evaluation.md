# Evaluation baselines

Run `python -m evals.run_baselines --output evals/results/baseline-v1.json`.

This is a deterministic, no-network harness over synthetic fixtures, fake embeddings, and recorded QA outputs—not a live-model benchmark.

| Suite | Dataset cases | Prediction source | Measured results |
| --- | ---: | --- | --- |
| Retrieval | 9 | deterministic fake embedding | Recall@1/3/5: 0.6667/1.0000/1.0000; MRR: 0.7963 |
| Grounded QA | 7 | recorded output | grounded success: 0.5714; citation validity: 0.6667; invalid citation rate: 0.3333 |

## Methodology and limitations

Retrieval preserves chunk/page provenance and reports cross-document leakage separately. Grounded-QA validates recorded citations against retrieved context; it does not measure live-model answer quality. Classification and extraction fixtures currently support evaluator/validator correctness only because they have no independent stored predictions; no quality score is published for them.
