# Security policy

Report vulnerabilities through GitHub's private vulnerability reporting on this repository (Security tab), not in a public
issue. Only the latest `main` is supported before 1.0.

In scope: leaked secrets in manifests, results or reports; paths that expose verifier tests or reference solutions to an
agent or to training data; code execution from a config or dataset file.

Agents execute model-written commands. When the Harbor runner exists, run it only in a sandbox with no credentials other
than the model endpoint's, and restrict network access. Run the model endpoint on a trusted network; vLLM's runtime LoRA
and weight-update endpoints are administrative and must not be exposed.
