# DecisionGate

## Your software probably needs this.

## A simple question should be simple

You’re building an application. A user types, “Any chance I could come in next Tuesday?” Your software needs to make one simple decision: is this person asking for an appointment?

Do you really have to get an API key, send their text over the network, and pay for an API call just to answer that? Or integrate with Ollama or TensorFlow, manage a separate runtime, and turn a simple question into an infrastructure project? And most of the time, you end up BEGGING for JSON! OMG wouldn't you rather giant squid on the lips instead?

```prompt
User text: "Any chance I could come in next Tuesday?"

Is this user asking for an appointment?

Please return ONLY valid JSON: {"appointment_requested": true}
Use false if the answer is no. An actual boolean, not the string "false".
No explanation. No Markdown. No triple-quoted code fences. No extra keys.
Do not say "Certainly!"; just skip to the JSON.

Please. I have a family. Just valid JSON... I'm begging you.
```

You're thinking: “I wish I could just load a normal library and call a normal function.”

**NOW YOU CAN!** In MANY languages and platforms; python example:

```python
from decisiongate import is_yes

appointment_requested = is_yes(
    "Any chance I could come in next Tuesday?",
    "Is this person asking for an appointment?",
)
```

**DecisionGate is a SOFTWARE COMPONENT, not an AI!** OK, there is a small trained model inside, but it is so small and insulated that you don't need to know about it. There is no chat, no prompt, no agent, and nothing to "talk to": it's a function that takes text and a question and returns a boolean. Ship it with your application and call a function. The same way your grandfather used software components: a library, some arguments, a return value. The kind of thing you did back in the 1990s.

**No Ollama. No llama.cpp. No TenserFlow, No agent harness. No network! Just a goddamn software component!**

## Languages and platforms

**An offline yes/no decision component for your software.** Ready-to-use interfaces for **Python, Java, TypeScript/JavaScript, C, and Rust** run on Apple silicon Macs, Windows x64, and Linux x64. The C interface also makes bindings possible for C++, C#, Go, Swift, Ruby, and other languages that can call C libraries.

| Platform             | Library     | Status                                  |
| -------------------- | ----------- | --------------------------------------- |
| Mac M1 and newer     | `.dylib`    | Experimental build, tested locally      |
| Windows x64          | `.dll`      | Built and tested on Windows 11          |
| Linux x64, glibc     | `.so`       | Built and tested on Omarchy Linux       |
| Desktop web browsers | WebAssembly | Tested in Chromium, Firefox, and WebKit |

**The same trained weights everywhere.** Native applications and browsers use the same decision data, tokenizer, and rules, with tested agreement between their answers.

The component runs on a CPU. Your application needs no separate runner or GPU setup. See [release bundles](released/README.md) for packaging details.

The same call, from whatever you already write in:

```java
Decisions.isYes(text, "Is the customer asking to cancel?")      // Java
```

```typescript
await isYes(text, "Is this reporting a service outage?");        // TypeScript / Node.js
```

```c
dg_is_yes(text, strlen(text), q, strlen(q), NULL, &yes);         /* C */
```

```rust
dg_is_yes(text.as_ptr(), text.len(), q.as_ptr(), q.len(), null(), &mut yes)  // Rust
```

**Even inside a web browser**, with the text never leaving the user's device:

```javascript
import { isYes } from "decisiongate/web";
```

Complete, runnable examples for every language, including probabilities, criteria, thresholds, and multiple-choice decisions, are in [EXAMPLE_USAGE.md](EXAMPLE_USAGE.md).

## Your answer. Your rules.

Supply different content and a yes/no question on each call. Optional criteria let you spell out what counts as yes or no. The first call initializes the component automatically; later calls reuse it.

| Language                | Boolean                | Probability of yes      |
| ----------------------- | ---------------------- | ----------------------- |
| Python                  | `is_yes(...)`          | `is_yes_p(...)`         |
| Java                    | `Decisions.isYes(...)` | `Decisions.isYesP(...)` |
| JavaScript / TypeScript | `await isYes(...)`     | `await isYesP(...)`     |
| C                       | `dg_is_yes(...)`       | `dg_is_yes_p(...)`      |
| Rust (via the C ABI)    | `dg_is_yes(...)`       | `dg_is_yes_p(...)`      |

**P means probability of yes**, from zero to one. Boolean calls return true when that probability is at least **0.5** by default. Python accepts `threshold=0.90`; Java accepts a threshold overload, as above; C offers `dg_is_yes_at_threshold`. Choose a threshold using examples from your application, or use probabilities to reserve an uncertain range for review. Errors are reported separately, never disguised as “no.”

Install a [Python wheel](released/python/README.md), add the [Java JARs](java/README.md), install a [Node.js package](javascript/README.md), link the [C library](code/README.md), or call it from [Rust](examples/rust_smoke/). Local packages are under `released/`; registry publication comes later. For custom bundles and explicit resource management, see [the interface specification](specs/component-api.md).

## What if this gives a wrong answer?

# GREAT!

**That means you can add training data, retrain the model yourself right here in this project, and contribute your training data to the project so the whole world can benefit!**

A wrong answer from a closed API is a dead end: you file a ticket and hope. A wrong answer here is a bug report you can fix yourself, the same way you'd patch any other open-source component. The training data is plain text files in this repository, the training recipe runs on an ordinary laptop, and a pull request with your examples makes the next release better for everyone.

**Open weights. Open training data. Open recipes.**

1. **Catch a mistake.** Save the content and question, supply the correct answer, and explain why.
2. **Teach your own copy.** Clone the repository, add your examples, and [retrain and test](specs/accuracy-v2.md) a version you can ship.
3. **Share the improvement.** Submit examples through a normal Git pull request. Reviewed contributions improve the shared training data; tested improvements become new releases.

You need neither a GPU nor machine-learning expertise to contribute an example. You can also retrain privately without sharing your data. A correction is useful evidence, not a guaranteed fix: evaluation checks whether it helps without breaking earlier decisions.

We intend to publish releases and training assets, likely on Hugging Face alongside this repository. Our training data is open; that does not mean we possess the upstream pretraining corpus. See [contribution and training details](specs/open-training.md).

## What you can use today

The experimental Mac bundle is about **394 MB**; the browser bundle is about **345 MB**. Both run entirely inside your application, with no telemetry, remote inference fallback, or per-call bill. Browser assets are delivered with your web app. It was fine-tuned on an M1 Pro Mac with 32 GB of memory. Project code and current weights are both Apache-2.0; dependencies carry their own [license notices](notices/README.md).

**Accuracy is still experimental:** the current version answered **59 of 80 fresh synthetic test cases correctly**, up from 42 for the original. That leaves 21 errors, and there is no independent human-reviewed benchmark. The examples above illustrate the interface, not a guarantee of reliable appointment, duplicate, or cancellation detection. See [measured accuracy, size, and speed](reports/accuracy-v2.md).

Version one handles English text and yes/no questions. Other decision types come later.

Building it? Start with the [developer specifications](specs/README.md).
