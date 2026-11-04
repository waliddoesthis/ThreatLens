"""Answer-eval helpers: citation parsing, citation metrics, judge parsing. No models, no network."""

import sys
from pathlib import Path

from threatlens.citations import extract_citations, mentioned_ids
from threatlens.index import embedding_prefixes

sys.path.insert(0, str(Path(__file__).parents[1] / "eval"))
from judge import parse_verdict  # noqa: E402
from metrics import citation_metrics, statements  # noqa: E402
from run_retrieval_eval import usable_questions  # noqa: E402


def test_extract_citations_single_grouped_and_noise():
    text = (
        "PowerShell is abused [attack:T1059.001]. Detect it [sigma:abc-1, attack:T1059.001; "
        "kev:CVE-2024-3400]. See [the docs](https://x) and [1]."
    )
    assert extract_citations(text) == ["attack:T1059.001", "sigma:abc-1", "kev:CVE-2024-3400"]


def test_mentioned_ids():
    assert mentioned_ids("CVE-2021-44228, T1059.001, t1003 and M1032; not T12") == {
        "CVE-2021-44228",
        "T1059.001",
        "T1003",
        "M1032",
    }


def test_statements_skip_headings_and_fragments():
    ans = "**Summary**\nPowerShell is widely abused by attackers [attack:T1059.001].\n- ok\n## Details"
    assert statements(ans) == ["PowerShell is widely abused by attackers [attack:T1059.001]."]


def test_citation_metrics():
    ans = (
        "**Summary**\n"
        "Log4Shell is exploited in the wild [kev:CVE-2021-44228].\n"
        "- It maps to T1190 and was used with T1059.009 [attack:T1190] [attack:T9999].\n"
        "- Patching is the main mitigation for this vulnerability."
    )
    provided = ["kev:CVE-2021-44228", "attack:T1190"]
    m = citation_metrics(ans, provided, {"kev:CVE-2021-44228"}, "Log4j CVE-2021-44228 T1190")
    assert m["citation_validity"] == 2 / 3  # attack:T9999 was never provided
    assert m["gold_cited"] == 1.0
    assert m["statement_coverage"] == 2 / 3
    assert m["unsupported_ids"] == 1.0  # T1059.009 is in no source
    # gold not retrieved -> generation can't be blamed, so gold_cited is undefined
    assert citation_metrics(ans, provided, {"sigma:x"}, "")["gold_cited"] is None
    assert citation_metrics("No sources cover this.", [], set(), "")["citation_validity"] is None


def test_parse_verdict():
    v = parse_verdict(
        'Sure: {"claims": [{"claim": "a", "supported": true}, {"claim": "b", "supported": false}],'
        ' "relevancy": 4}'
    )
    assert v["faithfulness"] == 0.5 and v["relevancy"] == 4.0
    assert parse_verdict("no json here") is None
    assert parse_verdict('{"claims": [], "relevancy": 9}') == {
        "claims": [],
        "faithfulness": None,
        "relevancy": None,
    }


def test_usable_questions_drops_stale_gold_ids():
    qs = [
        {"id": "a", "gold_ids": ["attack:T1", "attack:OLD"]},
        {"id": "b", "gold_ids": ["certfr:GONE"]},
    ]
    assert usable_questions(qs, {"attack:T1"}) == [{"id": "a", "gold_ids": ["attack:T1"]}]


def test_embedding_prefixes():
    assert embedding_prefixes("BAAI/bge-small-en-v1.5")[0].startswith("Represent this sentence")
    assert embedding_prefixes("intfloat/multilingual-e5-small") == ("query: ", "passage: ")
    assert embedding_prefixes("BAAI/bge-m3") == ("", "")
    assert embedding_prefixes("sentence-transformers/all-MiniLM-L6-v2") == ("", "")
