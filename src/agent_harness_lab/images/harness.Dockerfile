# One harness, installed in the paths Harbor's own installers use. Takes no secrets.
ARG BASE
FROM ${BASE} AS build
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl
ARG NVM_VERSION NODE_VERSION
RUN mkdir -p /root/.nvm /root/.harbor \
    && curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" \
      | env -u NODE_VERSION METHOD=script PROFILE=/dev/null NVM_DIR=/root/.nvm bash \
    && set +u && . /root/.nvm/nvm.sh && nvm install "${NODE_VERSION}" && nvm alias default "${NODE_VERSION}" \
    && rm -rf /root/.nvm/.cache
ARG NPM_INSTALL PACKAGE
RUN set +u && . /root/.nvm/nvm.sh && npm install ${NPM_INSTALL} --no-audit --no-fund "${PACKAGE}"
ARG VERSION_COMMAND VERSION
RUN set +u && . /root/.nvm/nvm.sh && ${VERSION_COMMAND} --version 2>&1 | tail -n 1 | tee /dev/stderr \
    | grep -E "(^|[^0-9.])${VERSION//./\\.}$"

FROM scratch
COPY --from=build /root/.nvm /root/.nvm
COPY --from=build /root/.harbor /root/.harbor
