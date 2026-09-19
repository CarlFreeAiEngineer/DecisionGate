# DecisionGate

## Your software probably needs this.

## A simple question should be simple

You’re building an application. A user types, “Any chance I could come in next Tuesday?” Your software needs to make one simple decision: is this person asking for an appointment?

Do you really have to get an API key, ship their **potentially private** text across the internet to a company they've never heard of, and pay for an API call just to answer that? Or integrate with Ollama or TensorFlow, manage a separate runtime, and turn a simple question into an infrastructure project? And most of the time, you end up BEGGING for JSON! OMG wouldn't you rather giant squid on the lips instead?

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

**It's like a regex library.** Every language has one. You hand it a pattern and some text, and you get back a boolean. Nobody runs a regex server, nobody has a regex API key, and nobody thinks of it as AI. DecisionGate is the same kind of thing, except the pattern is a question in plain English: `is_yes(text, "Is this person asking for an appointment?")`. Reach for it on the day the regex stops working. Which, for anything a person wrote in their own words, is **right now**.

**The silent half of the brain.** In split-brain patients only one hemisphere can talk; the other still answers questions correctly, by pointing, and never explains itself ([CGP Grey explains](https://www.youtube.com/watch?v=wfYbgdo8e-8)). Language models are the talking half. DecisionGate is the silent half: it reads, decides, points at yes or no or one of your options, and says nothing else. Give your code both.

**If you know [JEV](https://www.jevai.org/)** from TypeSafe AI: the brain under the hood is similar, a small classifier that takes text plus a question and returns a typed answer with a probability instead of generating prose ([LangChain's write-up](https://www.langchain.com/blog/building-a-harness-with-jev)). But JEV is a paid API on someone else's server. DecisionGate is a library file in your build. For a working programmer that is a night-and-day difference: no account, no network, no bill, no one else's outage, and the model is yours to retrain.

## How it compares

Every row below can answer "is this person asking for an appointment?" The differences are the painful parts: what you have to set up, what shape the answer comes back in, and what you do when it's wrong.

| | Setup | The answer comes back as | Offline | Wrong answer? |
| --- | --- | --- | --- | --- |
| **DecisionGate** | Add a library | A boolean | Yes | Add data, retrain |
| **Regex / keywords** | None | A boolean, for cases you thought of | Yes | Add a pattern, break another |
| **LLM API** | API key, billing, network | JSON, if you beg | No | Prompt harder and hope |
| **Local LLM** (Ollama, llama.cpp) | Runtime, model files, GPU | JSON, if you beg | Yes | Prompt harder and hope |
| **Jev** (TypeSafe AI) | API key, waitlist, network | Typed answer + probability | No | Can't; it's hosted |
| **Needle 3** (Cactus) | Python package or C library | JSON tool call | Yes | LoRA fine-tune |
| **Zero-shot NLI model** | PyTorch or ONNX, in Python | Logits you threshold | Yes | Write the training code |

What the table hides:

- **Regex and keyword matching** is what most software actually does today, and it's the right tool until the day someone writes "no rush, but could I come in Tuesday?" Every fuzzy case becomes another pattern, and every new pattern breaks an old one. DecisionGate is for the decisions that were never really regular expressions.
- **A hosted LLM** is the most flexible and the best on hard cases. It is also an API key, a bill, a network dependency, your users' text on someone else's server, and an afternoon of begging for JSON. That is the reason this project exists.
- **A local LLM through Ollama or llama.cpp** removes the network and the bill and replaces them with a runtime to install, model files to manage, a GPU to wish for, and the same begging for JSON. It turns a simple question into an infrastructure project.
- **Jev** is the closest in spirit: a purpose-built decision model that takes text plus a question and returns a typed answer with a probability, not prose. No begging. But it is a hosted API in early access behind a waitlist, at $0.042 per million input tokens, with 70 to 500 milliseconds plus network per call. Your users' text leaves your machine every time, and you cannot retrain it.
- **Needle 3** is a remarkable piece of engineering aimed at a different job: tool calling, structured extraction, and embeddings on phones, wearables, and microcontrollers, in 8 to 29 MB under Apache-2.0. You can get a classification out of it by defining one tool per label, but there is no `is_yes(text, question)`, and it ships as a Python package or C library rather than ready-made Java, Node, browser, and Rust interfaces.
- **A zero-shot NLI model** such as `facebook/bart-large-mnli` is what DecisionGate is built from, one layer down. Free and open, and a fine choice if you already live in Python with PyTorch installed and want to write the tokenization, prompting, thresholds, calibration, and packaging yourself. DecisionGate is that work, done once, shipped as a component for six languages.

Numbers are from each project's own published material as of September 2026 and will drift; check the source before relying on them.

## What if this gives a wrong answer?

# GREAT!

**That means you can add training data, retrain the model yourself right here in this project, and contribute your training data to the project so the whole world can benefit!**

A wrong answer from a closed API is a dead end: you file a ticket and hope. A wrong answer here is an improvement you can make yourself. Write down the text, the question, and the right answer, add them to the training data, and retrain. The training data is plain text files in this repository, and the training recipe runs on an ordinary laptop. Keep the improved model for yourself, or send your examples back in a pull request and the next release gets better for everyone.

**Open weights. Open training data. Open recipes.**

1. **Catch a mistake.** Save the content and question, supply the correct answer, and explain why.
2. **Teach your own copy.** Clone the repository, add your examples, and [retrain and test](specs/accuracy-v2.md) a version you can ship.
3. **Share the improvement.** Submit examples through a normal Git pull request. Reviewed contributions improve the shared training data; tested improvements become new releases. The step-by-step version is in [CONTRIBUTING.md](CONTRIBUTING.md).

You need neither a GPU nor machine-learning expertise to contribute an example. You can also retrain privately without sharing your data. A correction is useful evidence, not a guaranteed fix: evaluation checks whether it helps without breaking earlier decisions.

We intend to publish releases and training assets, likely on Hugging Face alongside this repository. Our training data is open; that does not mean we possess the upstream pretraining corpus. See [contribution and training details](specs/open-training.md).

## What you can use today

The experimental Mac bundle is about **229 MB**; the browser bundle is about **181 MB**. Weights are stored as float16 and computed in float32, which halved the download without changing any test decision; Windows and Linux bundles are still the previous 394 MB version until they are rebuilt. Both run entirely inside your application, with no telemetry, remote inference fallback, or per-call bill. Browser assets are delivered with your web app. It was fine-tuned on an M1 Pro Mac with 32 GB of memory. Project code and current weights are both Apache-2.0; dependencies carry their own [license notices](notices/README.md).

**Accuracy is still experimental:** version 0.3.0 answered **62 of 80 fresh synthetic yes/no test cases** correctly (59 for the previous version, 42 for the original) and **14 of 20 held-out multiple-choice cases**. That leaves plenty of errors, and there is no independent human-reviewed benchmark. The examples above illustrate the interface, not a guarantee of reliable appointment, duplicate, or cancellation detection. See [measured accuracy, size, and speed](reports/accuracy-v3.md).

The current version handles English text, yes/no questions, and multiple choice over caller-supplied options. Other decision types come later.

Building it? Start with the [developer specifications](specs/README.md).
