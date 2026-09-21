# Guava Voice Index (GVI)

## Composite Scoring Framework

v1.0 | September 2026

---

## 1. Overview

The GVI is a 0-100 composite score for voice agent quality. It combines automated metrics from open-source frameworks (EVA-Bench and CoVAL) with blind human evaluations scored by a third-party evaluation panel across five pillars. Content correctness accounts for 60% of the score; voice experience accounts for 40%.

---

## 2. Composite Formula

```
GVI = 10 × Responsiveness + 15 × Conversational Flow + 30 × Fidelity + 30 × Resolution + 15 × TTS Quality
```

---

## 3. Pillar Definitions

| Pillar                  | Weight | Category   | Primary Signal                         |
|:------------------------|:------:|:-----------|:---------------------------------------|
| **Responsiveness**      |     10 | Experience | How fast does it reply?                |
| **Conversational Flow** |     15 | Experience | Does it know when to talk and stop?    |
| **Fidelity**            |     30 | Content    | Did it say true things?                |
| **Resolution**          |     30 | Content    | Did the job get done?                  |
| **TTS Quality**         |     15 | Experience | Does it sound natural?                 |

---

### 3.1 Responsiveness (10 pts)

Pure speed: time from caller done speaking to agent audio. Floor = 0.3s (perfect), ceiling = 4.0s (zero).

| Metric          | Source         | Scale                                  | Weight |
|:----------------|:---------------|:---------------------------------------|:------:|
| response_speed  | EVA diagnostic | Seconds (transformed to 0-1 scoring)  |   0.50 |
| response_speed  | Human eval     | % win vs. human                        |   0.50 |

### 3.2 Conversational Flow (15 pts)

Timing judgment, interruption handling, conciseness. Combines automated and human signals.

| Metric                   | Source     | Scale                 | Weight |
|:-------------------------|:-----------|:----------------------|:------:|
| turn_taking              | EVA-X      | 0-1                   |   0.25 |
| conciseness              | EVA-X      | 0-1                   |   0.25 |
| interruption_score       | Human eval | % win rate vs. human  |   0.25 |
| content_relevance_score  | Human eval | % win rate vs. human  |   0.25 |

### 3.3 Fidelity (30 pts)

Content accuracy: did the agent say true things and render them correctly? Includes STT accuracy because mishearing the caller is functionally equivalent to hallucinating.

| Metric                | Source                      | Scale                  | Weight |
|:----------------------|:----------------------------|:-----------------------|:------:|
| faithfulness          | EVA-A (Claude Opus judge)   | 0-1                    |   0.50 |
| agent_speech_fidelity | EVA-A (Gemini audio)        | 0-1                    |   0.30 |
| stt_wer               | CoVAL Voice AI Benchmark    | % accuracy (1 - WER)   |   0.20 |

### 3.4 Resolution (30 pts)

Task completion: did the caller's problem get solved? conversation_progression is here (not Conversational Flow) because looping endlessly is a resolution failure.

| Metric                   | Source                | Scale | Weight |
|:-------------------------|:----------------------|:------|:------:|
| task_completion          | EVA-A (DB hash)       | 0-1   |   0.60 |
| conversation_progression | EVA-X (LLM judge)     | 0-1   |   0.40 |

### 3.5 TTS Quality (15 pts)

Perceptual voice quality. Human eval is the primary signal.

| Metric      | Source     | Scale             | Weight |
|:------------|:-----------|:------------------|:------:|
| tts_quality | Human eval | % win vs. human   |   1.00 |

---

## 4. Validation Gates

Scenarios must pass all gates before contributing to scores. Failed gate = scenario discarded.

| Gate                    | Check                                      | Threshold |
|:------------------------|:-------------------------------------------|:----------|
| user_behavioral_fidelity | Simulated user didn't corrupt the test    | >= 0.5    |
| conversation_valid_end  | Call ended with proper end_call             | >= 0.5    |
| user_speech_fidelity    | User simulator spoke correctly             | >= 2.0    |

---

## 5. Duplication Avoidance

Each concept is assigned to exactly one pillar to prevent double-counting.

| Concept                 | Assigned To        | Not In          | Why                                      |
|:------------------------|:-------------------|:----------------|:-----------------------------------------|
| Interruption handling   | Conversational Flow | Responsiveness | Judgment, not speed                       |
| agent_speech_fidelity   | Fidelity           | TTS Quality     | Word correctness, not naturalness         |
| conciseness             | Conversational Flow | Resolution     | Conversational dynamics, not task outcome |
| conversation_progression | Resolution         | Conversational Flow | Goal advancement, not timing          |
| stt_wer                 | Fidelity           | Resolution      | Input accuracy, not task outcome          |
| speakability            | TTS Quality        | Fidelity        | Voice-friendliness, not content truth     |

---

## 6. Human Evaluation Protocol

**Perceived Responsiveness (Pillar 1)**
Pairwise A/B test. Evaluators pick which agent feels faster and more responsive. Min 10 evaluators per pair. Vetted evaluator panel.

**Interruption Score (Pillar 2)**
Pairwise A/B test. Evaluators pick which agent more naturally recovered from the interruption. Min 10 evaluators per pair. Vetted evaluator panel.

**Content Relevance (Pillar 2)**
Pairwise A/B test. Evaluators pick which agent's dialog more naturally suited the conversation dynamics. Min 10 evaluators per pair. Vetted evaluator panel.

**TTS Quality (Pillar 5)**
Pairwise A/B test. Evaluators pick which agent voice sounds more natural. Min 10 evaluators per pair. Vetted evaluator panel.

---

## 7. Methodology

### Automated Layer

The GVI pulls from two open-source frameworks:

- **EVA-Bench** provides metrics for task completion, conversation progression, turn-taking, conciseness, faithfulness, agent speech fidelity, and latency through bot-to-bot audio evaluation across enterprise scenarios.
- **CoVAL** provides speech recognition word error rate.

> **Note:** The latency submetric is log-normalized from raw metrics to keep the total possible score at 100 and the minimum at 0. All other automated submetrics are scored 0 or 1.

### Human Evaluation Layer

The human layer is a blind pairwise evaluation run by a third-party evaluation panel. Evaluators compare systems against live human agents handling the same calls through both audio listening tests and transcript reviews. This produces the perceived responsiveness, interruption handling, content relevance, and TTS quality submetrics.

---

## Submission

To submit a voice agent system for GVI evaluation, visit [WEBSITE URL].
