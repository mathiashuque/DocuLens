from retrieval.tokenizer import estimate_tokens


def test_estimate_tokens_counts_whitespace_words() -> None:
    assert estimate_tokens("one two three") == 3


def test_estimate_tokens_blank_text_is_zero() -> None:
    assert estimate_tokens("   \n\t  ") == 0


def test_estimate_tokens_deterministic() -> None:
    text = "The quick brown fox jumps over the lazy dog."
    assert estimate_tokens(text) == estimate_tokens(text)
