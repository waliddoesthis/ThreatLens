# The demo recording

The GIF at the top of the README is recorded by a script, not by hand:
[`scripts/record_demo.py`](../scripts/record_demo.py) drives the running app in a headless
browser, asks the questions below, takes a screenshot every 0.4 s and assembles the frames. It
runs on the same machine and models the benchmarks used, so what it shows is what was measured.

```bash
pip install playwright pillow && playwright install chromium
ROUTER_MODE=always_small streamlit run app/streamlit_app.py --client.toolbarMode=minimal
# ask one question first (the first answer loads the models and is much slower), then:
python scripts/record_demo.py --shots 1 2 3
```

What keeps it honest: the wait before the first words is played 8 times faster and labelled as
such on every frame, the writing is played at real speed, and each frame shows the real seconds
since "Ask". The right-hand column of the app shows the measured first-token and full-answer times.

## Shot list
`--shots` picks among these:

| # | Input | What it shows | Why it is in the demo |
|---|---|---|---|
| 1 | `How do attackers dump credentials from LSASS, and which Sigma rules detect it?` | "6 sources" appears, then the answer writes itself | Cited, streamed answer: the core of the project |
| 2 | `rundll32.exe C:\Windows\System32\comsvcs.dll, MiniDump 624 C:\temp\lsass.dmp full` | The answer names T1003.001 | A raw command line, no technique named: the Sigma → technique links find it (alerts Recall@5 0.15 → 0.33) |
| 3 | `Is CVE-2024-3400 exploited in the wild and what should I do?` | The KEV line in the answer (date added, ransomware use) with its `[kev:…]` citation | Exploitation status comes from data, not from the model's memory |
| 4 | Turn on **Agent mode**, ask `How do I detect and mitigate Kerberoasting?` | The status box listing the tool calls, then **What the agent did** on the right | The agent's steps are visible (it was not shown to beat the pipeline) |
| 5 | `Comment détecter le vol d'identifiants dans la mémoire de LSASS ?` | A French question answered from English sources | Query translation (French Recall@5 0 → 5 of 5) |

Shots 1 to 3 are the default.

