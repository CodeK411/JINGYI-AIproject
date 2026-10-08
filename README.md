# VeriPolicy interactive demo

This branch contains the static browser demo published by GitHub Pages.

The original Python project is in the `main` branch under `04-veripolicy-rag`.
The demo runs its CPU/LSA retrieval model, applicability filters, reranking,
rule conflict checks, extractive answers and version comparison in the browser.
It uses 29 fictional policy documents and does not require a server or API key.
It does not call an LLM or run the Agent loop. Evaluation charts display the
original saved benchmark results; they are not new online evaluation runs.

The browser port was checked against 432 Python requests: answers, citations
and refusal decisions matched; five cases had different candidate ordering
and the maximum confidence difference was below 0.001. Free-form paraphrases
can still retrieve irrelevant evidence, so users should inspect the citations.

Assets resolve relative to this deployment, including GitHub project paths.
