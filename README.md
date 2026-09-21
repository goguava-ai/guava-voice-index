# Guava Voice Index (GVI)

The Guava Voice Index (GVI) is a benchmark for measuring voice agent quality. It combines automated evaluation from open-source frameworks with blind human evaluation scored by a third-party evaluation panel.

---

## Five Pillars

The GVI scores voice agents across five pillars:

| Pillar                  | What it measures                                                                                      |
|:------------------------|:------------------------------------------------------------------------------------------------------|
| **Responsiveness**      | How quickly the agent responds, both in automated latency metrics and as perceived by human evaluators |
| **Conversational Flow** | How naturally the agent handles turn-taking, silence, and the back-and-forth of a real conversation    |
| **Fidelity**            | How accurately the system hears, understands, and speaks                                              |
| **Resolution**          | Whether the agent completes the task the caller needed                                                |
| **Speech Quality**      | How natural the agent's voice sounds to a human listener                                              |

---

### Responsiveness

| Submetric                | What it measures                                                                    | Source           |
|:-------------------------|:------------------------------------------------------------------------------------|:-----------------|
| Latency                  | Mean time between the caller finishing speaking and the agent starting its response  | EVA-Bench        |
| Perceived responsiveness | Whether the agent feels fast or slow to a human listener                            | Human evaluation |

### Conversational Flow

| Submetric              | What it measures                                                                | Source           |
|:-----------------------|:--------------------------------------------------------------------------------|:-----------------|
| Turn-taking            | How cleanly the agent handles transitions between speaker turns                 | EVA-Bench        |
| Conciseness            | Whether the agent says what it needs to without unnecessary filler              | EVA-Bench        |
| Interruption handling  | How the agent responds when a caller talks over it or cuts in                   | Human evaluation |
| Content relevance      | Whether what the agent says fits the moment in the conversation                 | Human evaluation |

### Fidelity

| Submetric              | What it measures                                                                    | Source           |
|:-----------------------|:------------------------------------------------------------------------------------|:-----------------|
| Faithfulness           | Whether the agent says things that are true and aligned with its knowledge base      | EVA-Bench        |
| Agent speech fidelity  | Whether the spoken output accurately reflects what the agent intended to say         | EVA-Bench        |
| STT word error rate    | How accurately speech recognition transcribes what the caller said                   | CoVAL            |

### Resolution

| Submetric                | What it measures                                                              | Source           |
|:-------------------------|:------------------------------------------------------------------------------|:-----------------|
| Task completion          | Whether the agent completed the task the caller needed                        | EVA-Bench        |
| Conversation progression | Whether the conversation moved forward logically toward resolution            | EVA-Bench        |

### Speech Quality

| Submetric   | What it measures                                    | Source           |
|:------------|:----------------------------------------------------|:-----------------|
| TTS quality | How natural and lifelike the agent's voice sounds   | Human evaluation |

---

## Methodology

### Automated Layer

The GVI pulls from two open-source frameworks:

- **EVA-Bench** provides metrics for task completion, conversation progression, turn-taking, conciseness, faithfulness, agent speech fidelity, and latency through bot-to-bot audio evaluation across enterprise scenarios.
- **CoVAL** provides speech recognition word error rate.

> **Note:** The latency submetric is log-normalized from raw metrics. All other automated submetrics are scored 0 or 1.

### Human Evaluation Layer

The human layer is a blind pairwise evaluation run by a third-party evaluation panel. Evaluators compare systems against live human agents handling the same calls through both audio listening tests and transcript reviews. This produces the perceived responsiveness, interruption handling, content relevance, and TTS quality submetrics.

---

## Scoring

The GVI is an index with a maximum score of **100** and a minimum score of **0**. Each pillar has a fixed weight, and each submetric has a weight within its pillar.

| Pillar                  | Weight | Submetric                | Submetric Weight | Max Points |
|:------------------------|:------:|:-------------------------|:----------------:|:----------:|
| **Responsiveness**      |     10 | Latency                  |             0.50 |       5.00 |
|                         |        | Perceived responsiveness |             0.50 |       5.00 |
| **Conversational Flow** |     15 | Turn-taking              |             0.25 |       3.75 |
|                         |        | Conciseness              |             0.25 |       3.75 |
|                         |        | Interruption handling    |             0.25 |       3.75 |
|                         |        | Content relevance        |             0.25 |       3.75 |
| **Fidelity**            |     30 | Faithfulness             |             0.50 |      15.00 |
|                         |        | Agent speech fidelity    |             0.30 |       9.00 |
|                         |        | STT word error rate      |             0.20 |       6.00 |
| **Resolution**          |     30 | Task completion          |             0.60 |      18.00 |
|                         |        | Conversation progression |             0.40 |      12.00 |
| **Speech Quality**      |     15 | TTS quality              |             1.00 |      15.00 |

The log normalization on the latency submetric is designed to keep the total possible score at 100 and the minimum at 0.

---

## Submission

To submit a voice agent system for GVI evaluation, visit [WEBSITE URL].
