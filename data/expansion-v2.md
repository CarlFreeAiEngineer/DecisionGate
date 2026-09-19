# Question understanding expansion, version 2

`expansion-v2.jsonl` contains 240 original English synthetic examples, authored on 2026-09-17 by the OpenAI Codex assistant. The JSONL is the authoritative authored source. Each of 120 individually written passages has two independently written questions with different correct labels, explicit short rationales, and a shared source group and split. These are question contrasts, not a Cartesian expansion of reusable text templates.

| Split | Records | Yes | No | Without criteria | With criteria |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 180 | 90 | 90 | 130 | 50 |
| validation | 40 | 20 | 20 | 30 | 10 |
| calibration | 20 | 10 | 10 | 20 | 0 |
| total | 240 | 120 | 120 | 180 | 60 |

There is no test partition. The 90 passages without criteria cover everyday requests, negation, mixed intentions, cancellation and retention, refund versus exchange or information requests, appointments, same versus different issues, coding and billing, references to people and objects, conditional instructions, event order, permissions, and quoted or corrected instructions. Questions sometimes test an explicitly negative fact, such as absence of a condition, rather than treating positive wording as a yes label. The same topic words occur in both positive and negative examples. Cancellation, refunds, billing, and appointment terms alone cannot determine an answer.

The 30 passages with criteria require elementary numerical reasoning and boundary distinctions: inclusive versus strict limits, exact capacity, late arrival, elapsed time, net amounts, unit conversion, proportions, and remaining stock. Their criteria make comparison semantics and treatment of missing numerical evidence explicit. The question supplies the particular comparison, while the content supplies the facts. Other records ask only what their passage establishes; no real refund, medical, financial, or scheduling policy should be inferred.

Groups were assigned to splits during authoring, with distinct situations in each split. Every pair stays together. No evaluation-v2 data or model reports were read or used to author these records, and no model was run. The examples were created without customer records, web scraping, or copied external text. This is development material from one synthetic author, not an independent reviewed benchmark; related language and reasoning patterns still occur across splits. Calibration examples here all omit criteria, so this file alone cannot establish calibrated performance on numerical rules.

All records conform to schema version 1 described in [the data README](README.md) and carry `synthetic_unreviewed` review status. The author checked counts, paired label contrast, distinct record identifiers, and group separation; that is not independent human review. Only `content`, `question`, and `criteria` are model inputs. Rationales, labels, source names, identifiers, family names, and split names must not enter the input. Use this file explicitly in training manifests and preserve the split assignments.

The project intends these original examples and documentation to be available under CC0-1.0, to the extent rights in the generated material can be dedicated. See the [CC0 legal terms](https://creativecommons.org/publicdomain/zero/1.0/legalcode). This dedication does not apply to upstream model data or third-party material. Review labels and rights before adopting the data as a reviewed release.
