"""Query translation for French questions.

The corpus is English except CERT-FR, and both retrievers are English-first: BM25 shares no
token with "rançongiciel", and an English embedding model places French text poorly. Swapping
in a multilingual encoder only lifted French Recall@5 from 0 to 0.2-0.4 (docs/DECISIONS.md).
So a French question is translated once by the small model and searched in both languages:
the English query finds ATT&CK / KEV / Sigma, the original still finds CERT-FR.
"""

import re
from functools import lru_cache

from threatlens.config import settings

# function words that do not occur in English security text
_FR = frozenset(
    "le la les des du une un est sont dans pour sur avec par quels quelles quel quelle comment "
    "pourquoi qui que quoi où au aux ce cette ces et ou il elle ils elles ne pas se sa son ses "
    "leur leurs été être avoir fait entre vers chez sans sous après avant lors via contre "
    "concernant d l qu n s".split()
)
_EN = frozenset(
    "the is are was were of and to in for on with by which what how why who that this these "
    "those it does do did has have had from at as an be been not or".split()
)
_WORD = re.compile(r"[a-zàâäçéèêëîïôöùûüÿœ]+")
_ACCENT = re.compile(r"[àâçéèêëîïôùûœ]")

PROMPT = (
    "Translate this cybersecurity question from French to English. Keep product names, CVE "
    "ids, file names and command lines unchanged. Reply with the English translation only."
)


def is_french(text: str) -> bool:
    """Cheap language check: French function words (or accents) clearly outnumber English ones.

    Deliberately conservative: a false positive costs one LLM call, a pasted command line with
    a stray "la" must not trigger it.
    """
    words = _WORD.findall(text.lower())
    fr = sum(w in _FR for w in words) + (1 if _ACCENT.search(text.lower()) else 0)
    en = sum(w in _EN for w in words)
    return fr >= 2 and fr > en


@lru_cache(maxsize=512)
def to_english(question: str) -> str | None:
    """English translation by the small model, or None if the model is unavailable."""
    from threatlens.llm.client import complete

    try:
        res = complete(
            settings.small_model,
            [{"role": "system", "content": PROMPT}, {"role": "user", "content": question}],
            temperature=0.0,
            max_tokens=150,
        )
    except Exception as e:  # no model running: retrieval still works, in one language
        print(f"[translate] skipped ({type(e).__name__}); searching the original question only")
        return None
    lines = res.text.strip().splitlines()
    return (lines[0].strip().strip('"').strip() if lines else "") or None


def english_variant(question: str) -> str | None:
    """The extra English query to search with, when the question is French and translation is on."""
    if not settings.translate_queries or not is_french(question):
        return None
    return to_english(question)
