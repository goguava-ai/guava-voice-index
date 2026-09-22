## 🎙️ Guava Voice Index (GVI)
v1.0 | September 2026

### 📐 Composite Scoring Framework 

The Guava Voice Index (GVI) is a 0-100 composite score for voice agent quality. It combines automated metrics from open-source frameworks (EVA-Bench and CoVAL) with blind human evaluations scored by a third-party evaluation panel across five pillars.

```
GVI = 10 × Responsiveness + 15 × Conversational Flow + 30 × Fidelity + 30 × Resolution + 15 × TTS Quality
```

---

### 🏛️ Pillar Definitions

| Pillar                  | Weight | Category   | Primary Signal                         |
|:------------------------|:------:|:-----------|:---------------------------------------|
| **Responsiveness**      |     10 | Experience | How fast does it reply?                |
| **Conversational Flow** |     15 | Experience | Does it know when to talk and stop?    |
| **Fidelity**            |     30 | Content    | Did it say true things?                |
| **Resolution**          |     30 | Content    | Did the job get done?                  |
| **TTS Quality**         |     15 | Experience | Does it sound natural?                 |

---

#### Responsiveness (10 pts)

Pure speed: time from caller done speaking to agent audio. Floor = 0.3s (perfect), ceiling = 4.0s (zero).

| Metric          | Source         | Scale                                  | Weight |
|:----------------|:---------------|:---------------------------------------|:------:|
| response_speed  | EVA diagnostic | Seconds (transformed to 0-1 scoring)  |   0.50 |
| response_speed  | Human eval     | % win vs. human                        |   0.50 |

#### Conversational Flow (15 pts)

Timing judgment, interruption handling, conciseness. Combines automated and human signals.

| Metric                   | Source     | Scale                 | Weight |
|:-------------------------|:-----------|:----------------------|:------:|
| turn_taking              | EVA-X      | 0-1                   |   0.25 |
| conciseness              | EVA-X      | 0-1                   |   0.25 |
| interruption_score       | Human eval | % win rate vs. human  |   0.25 |
| content_relevance_score  | Human eval | % win rate vs. human  |   0.25 |

#### Fidelity (30 pts)

Content accuracy: did the agent say true things and render them correctly? Includes STT accuracy because mishearing the caller is functionally equivalent to hallucinating.

| Metric                | Source                      | Scale                  | Weight |
|:----------------------|:----------------------------|:-----------------------|:------:|
| faithfulness          | EVA-A (Claude Opus judge)   | 0-1                    |   0.50 |
| agent_speech_fidelity | EVA-A (Gemini audio)        | 0-1                    |   0.30 |
| stt_wer               | CoVAL Voice AI Benchmark    | % accuracy (1 - WER)   |   0.20 |

#### Resolution (30 pts)

Task completion: did the caller's problem get solved? conversation_progression is here (not Conversational Flow) because looping endlessly is a resolution failure.

| Metric                   | Source                | Scale | Weight |
|:-------------------------|:----------------------|:------|:------:|
| task_completion          | EVA-A (DB hash)       | 0-1   |   0.60 |
| conversation_progression | EVA-X (LLM judge)     | 0-1   |   0.40 |

#### TTS Quality (15 pts)

Perceptual voice quality. Human eval is the primary signal.

| Metric      | Source     | Scale             | Weight |
|:------------|:-----------|:------------------|:------:|
| tts_quality | Human eval | % win vs. human   |   1.00 |

---

### 🔬 Evaluation Protocol

#### 🤖 Automated Eval Protocol

The GVI pulls from two open-source frameworks:

- **EVA-Bench** provides metrics for task completion, conversation progression, turn-taking, conciseness, faithfulness, agent speech fidelity, and latency through bot-to-bot audio evaluation across enterprise scenarios.
- **CoVAL** provides speech recognition word error rate.

> **Note:** The latency submetric is log-normalized from raw metrics to keep the total possible score at 100 and the minimum at 0. All other automated submetrics are scored 0 or 1.

##### Validation Gates

Per EVA-Bench framework, scenarios must pass all gates before contributing to scores. Failed gate = scenario discarded.

| Gate                    | Check                                      | Threshold |
|:------------------------|:-------------------------------------------|:----------|
| user_behavioral_fidelity | Simulated user didn't corrupt the test    | >= 0.5    |
| conversation_valid_end  | Call ended with proper end_call             | >= 0.5    |
| user_speech_fidelity    | User simulator spoke correctly             | >= 2.0    |

#### 👂 Human Eval Protocol

All human metrics are collected through blind pairwise A/B tests run by an independent third-party evaluator panel. Evaluators compare systems against live human agents handling the same calls through both audio listening tests and transcript reviews. Minimum 10 evaluators per pair.

**Perceived Responsiveness**
Evaluators pick which agent feels faster and more responsive.

**Interruption Score**
Evaluators pick which agent more naturally recovered from the interruption.

**Content Relevance**
Evaluators pick which agent's dialog more naturally suited the conversation dynamics.

**TTS Quality**
Evaluators pick which agent voice sounds more natural.

---

### 📩 Submission

To submit a voice agent system for GVI evaluation, visit http://goguava.ai/gvi.

---

### 📚 References & Acknowledgments

This project utilizes the following open-source agent evaluation benchmarks:
* **[EVA Framework](https://github.com/ServiceNow/eva)** (v0.1.1) — An end-to-end framework developed by ServiceNow Research for evaluating conversational voice agents across task accuracy and user experience.
* **[Coval Voice AI Benchmarks](https://github.com/coval-ai/benchmarks)** - Public, open-source voice-AI benchmarking for STT and TTS providers.
