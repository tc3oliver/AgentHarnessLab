FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY fetch_source.py requirements.lock bug.patch hide.patch /tmp/build/
RUN python /tmp/build/fetch_source.py jmespath/jmespath.py 2812594e69d43098ef60f81f4efc404c071b0418 d06f2c3dbda981778fa39d7fca3a7ba49c4f2a797f66f08eefe9db22469b83cf /app
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
