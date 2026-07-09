"""Simple language detection."""

from langcodes import Language

from usdx_dl.inference import fasttext_np


def detect(text: str) -> tuple[Language, float]:
    """Detect the language of a given text.

    Args:
        text: The text to analyze. Longer texts generally yield more accurate results.

    Returns:
        A tuple of (language, confidence_score).
    """
    model = fasttext_np.load_model(quantized=True)
    pred = model.predict(text, k=1)
    if pred is None:
        return Language.get("und"), 0.0  # undetermined
    language = Language.get(pred[0].label)
    score = pred[0].score
    return language, score
