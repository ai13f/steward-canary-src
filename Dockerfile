FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} DATA_DIR=/data PORT=8080 PYTHONUNBUFFERED=1
# Warm the (simulated) cache before serving: ready after 3.5 minutes.
ENV READY_DELAY_S=210
WORKDIR /app
COPY app /app/app
COPY tests /app/tests
RUN adduser -D -u 10001 canary && mkdir /data && chown canary /data
USER 10001
EXPOSE 8080
CMD ["python", "-m", "app.server"]
