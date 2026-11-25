FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global user.name "Smoke Test" \
    && git config --global user.email "smoke@example.invalid" \
    && git config --global init.defaultBranch main \
    && git init /app/repo \
    && cd /app/repo \
    && printf 'timeout=30\nretries=3\n' > config.ini && git add . && git commit -q -m "Add base config" \
    && printf 'beta=on\n' > flags.txt && git add . && git commit -q -m "Add feature flags" \
    && printf 'timeout=0\nretries=3\n' > config.ini && git commit -q -am "Tune timeout" \
    && printf '\n[log]\nlevel=info\n' >> config.ini && git commit -q -am "Add log section"
WORKDIR /app
