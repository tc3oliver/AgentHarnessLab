# Prebuilt harness images

Harbor installs the harness into every sandbox. `agentlab images` does it once per harness version instead.

```bash
uv run agentlab images -c configs/experiments/baseline.yaml   # build what is missing, keep the rest
uv run agentlab eval   -c configs/experiments/baseline.yaml   # with runner.prebuilt: true
```

| Image | Content | Rebuilt when |
|---|---|---|
| `agentlab/harness-<name>:<version>-<hash>` | only `/root/.nvm` and `/root/.harbor` | recipe, Node or harness version changes |
| `agentlab/base-<task>:<hash>` | the task's own Dockerfile | `environment/` changes |
| `agentlab/task-<task>:<harness>-<hash>` | base plus harness | either part changes |

Nothing is pushed to a registry. A run stages a copy of each task whose `task.toml` gains only `docker_image`, set to the image
**id**, so a moved tag cannot change a run. Task hashes in results are those of the original task.

## Harbor versions

- **0.27.0**: Harbor's own `skip_install`. Harbor then reads the installed version instead of repeating the pin.
- **0.25.0** has no such option and installs on every trial. A small plugin (`harbor_plugin/agentlab_prebuilt.py`)
  subclasses Harbor's Pi and OpenCode and replaces only `install()` by a version check. Harbor itself is not modified.

With prebuilt images an unreadable or different version is an `infra_error`, never a graded trial.

## What is pinned

The harness version, Node, nvm and the installer's base image are pinned. npm dependencies and apt packages resolve at build time;
the image ids in `manifest.json` (`runtime.image.<harness>`, and one hash over all task images) and in each result identify the outcome of that build.
`agentlab compare` refuses runs that used different images.

## Limits

- Tasks must build from `environment/Dockerfile`, run as root, and use a glibc image. Compose tasks and tasks with their
  own `docker_image` are refused.
- Harbor's installers also leave `curl` (and for OpenCode distribution `nodejs` and `npm`) in the sandbox. Prebuilt images do not, so
  an agent may find fewer tools. Do not compare prebuilt with installed runs.
- No secret is used at build time and the build environment holds no API key. Remove images with
  `docker image rm` by name; a Docker prune would touch unrelated images.
