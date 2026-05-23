from __future__ import annotations
from .lrc import AnnotatedLine


def validate_batch(
    original: list[AnnotatedLine],
    response: list,
) -> tuple[list[dict] | None, str | None]:
    if not isinstance(response, list):
        return None, "response is not a JSON array"
    if len(response) != len(original):
        return None, f"expected {len(original)} lines, got {len(response)}"

    result = []
    for i, (orig, gen_obj) in enumerate(zip(original, response)):
        if not isinstance(gen_obj, dict) or "generated" not in gen_obj:
            return None, f"line {i + 1}: missing 'generated' field"
        generated = gen_obj["generated"]
        if not isinstance(generated, list):
            return None, f"line {i + 1}: 'generated' is not an array"
        for j, word in enumerate(generated):
            if not isinstance(word, list) or not all(isinstance(s, str) for s in word):
                return None, f"line {i + 1}, word {j + 1}: not an array of strings"
        orig_count = orig.syllable_count
        gen_count = sum(len(w) for w in generated)
        if orig_count != gen_count:
            return None, (
                f"line {i + 1}: syllable count mismatch — "
                f"expected {orig_count}, got {gen_count}"
            )
        result.append({"startMs": orig.start_ms, "original": orig.original, "generated": generated})
    return result, None
