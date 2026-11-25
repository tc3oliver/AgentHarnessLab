# A task image with one harness added.
ARG HARNESS TASK
FROM ${HARNESS} AS harness
FROM ${TASK}
COPY --from=harness /root/.nvm /root/.nvm
COPY --from=harness /root/.harbor /root/.harbor
