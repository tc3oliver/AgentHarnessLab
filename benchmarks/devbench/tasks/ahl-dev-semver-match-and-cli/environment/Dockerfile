FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY fetch_source.py requirements.lock bug.patch hide.patch /tmp/build/
RUN python /tmp/build/fetch_source.py python-semver/python-semver a4b7d337b1eb699ad4bad532a4b3fc68f8ec2408 0cac63fa8d1d67335aa316c2b97eae2394caaeae711672688cef2493988e08b8 /app
WORKDIR /app
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0+devbench
RUN pip install --no-cache-dir --no-deps -r /tmp/build/requirements.lock \
 && pip install --no-cache-dir --no-deps --no-build-isolation -e . \
 && if [ -s /tmp/build/bug.patch ]; then git apply /tmp/build/bug.patch; fi \
 && if [ -s /tmp/build/hide.patch ]; then git apply /tmp/build/hide.patch; fi \
 && rm -rf /tmp/build && find /app -name __pycache__ -prune -exec rm -rf {} + \
 && git init -q && git add -A \
 && git -c user.name=dev -c user.email=dev@example.invalid commit -qm "Initial import" \
 && git config --global --add safe.directory /app
