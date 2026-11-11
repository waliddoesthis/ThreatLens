# Recording the demo

A 60 to 90 second screen recording of the local app, embedded at the top of the README. It runs on
the same machine and models the benchmarks used, so what it shows is what was measured.

## Before recording
1. `.env`: `ROUTER_MODE=always_small` (everything stays on the local model) and `ANSWER_MODE=pipeline`.
2. Start Ollama and the app: `streamlit run app/streamlit_app.py`, open http://localhost:8501.
3. Ask one throwaway question first. The first answer loads the models and is much slower than the rest.
4. Browser window at 1280×720, zoom 110%, bookmarks bar hidden, light theme.
5. Recorder: ScreenToGif or OBS on Windows. Record the browser window only.

## Shot list
Type or paste each input, press **Ask**, and wait until the answer has finished before moving on.

| # | Input | What to show | Why it is in the demo |
|---|---|---|---|
| 1 | `How do attackers dump credentials from LSASS, and which Sigma rules detect it?` | "6 sources" appears, then the answer writes itself; scroll to the citations and hover one `[sigma:…]` link | Cited, streamed answer: the core of the project |
| 2 | `rundll32.exe C:\Windows\System32\comsvcs.dll, MiniDump 624 C:\temp\lsass.dmp full` | The answer names T1003.001; open the **Sources** panel on the right | A raw command line, no technique named: the Sigma → technique links find it (alerts Recall@5 0.15 → 0.33) |
| 3 | `Is CVE-2024-3400 exploited in the wild and what should I do?` | The KEV line in the answer (date added, ransomware use) with its `[kev:…]` citation | Exploitation status comes from data, not from the model's memory |
| 4 | Turn on **Agent mode**, ask `How do I detect and mitigate Kerberoasting?` | The status box listing the tool calls, then **What the agent did** on the right | The agent's steps are visible; say in the caption that it was not shown to beat the pipeline |
| 5 | `Comment détecter le vol d'identifiants dans la mémoire de LSASS ?` | A French question answered from English sources | Query translation (French Recall@5 0 → 5 of 5) |

Shots 1 to 3 are enough for a short version.

## Editing
- Keep the wait before the first words in at least one shot at real speed, and show the **First
  token** and **Full answer** figures on the right. In the other shots the wait may be sped up
  (4×), with "sped up" written on screen or in the caption. The measured numbers are in the README;
  the recording must not suggest better ones.
- Do not cut inside an answer while it is being written.
- Export a GIF under 10 MB (1280 px wide, 10 fps) to `docs/img/demo.gif`, and keep the full MP4 for LinkedIn.

## In the README
Under the title:

```markdown
![ThreatLens answering an alert with cited sources](docs/img/demo.gif)

*Local run: llama3.1:8b on an 8 GB RTX 2070. Waits are sped up 4× except in the first answer.*
```
