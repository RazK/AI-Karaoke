import re
import pyphen

_dic = pyphen.Pyphen(lang="en_US")


def split_syllables(word: str) -> list[str]:
    clean = re.sub(r"^[^a-zA-Z']+|[^a-zA-Z']+$", "", word)
    if not clean:
        return [word] if word.strip() else []
    for_pyphen = clean.replace("'", "")
    if not for_pyphen:
        return [clean]
    inserted = _dic.inserted(for_pyphen.lower())
    parts = inserted.split("-") if inserted else [for_pyphen.lower()]
    if not parts:
        return [clean]
    if clean[0].isupper():
        parts[0] = parts[0].capitalize()
    return parts


def count_syllables(word: str) -> int:
    return len(split_syllables(word))
