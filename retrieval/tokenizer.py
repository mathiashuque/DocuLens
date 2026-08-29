"""Deterministic, provider-independent token-count estimation.

Chunking and evaluation both need a token count to size chunks and report
usage. A real BPE tokenizer (e.g. `tiktoken`) is tied to one provider's
vocabulary and is not installed in this repository; adding it only for
chunk sizing would couple core chunking to a specific model family for no
measured accuracy benefit at this stage.

Instead this module counts whitespace-delimited words and treats that count
as the token estimate. This conservative approximation slightly
undercounts English prose (a true BPE tokenizer often splits words into
more than one token), which is the safe direction for a sizing budget:
actual chunks stay at or below the configured target rather than silently
exceeding it. The estimate is pure and deterministic across machines because
it depends only on `str.split()`.
"""


def estimate_tokens(text: str) -> int:
    """Return a deterministic, conservative token-count estimate for `text`.

    Empty or whitespace-only text estimates to zero.
    """
    return len(text.split())
