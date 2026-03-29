#!/bin/sh
set -eu

echo "[minio-init] Waiting for MinIO at ${MINIO_ENDPOINT}..."
until /usr/bin/mc alias set pfa-local "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  sleep 2
done

echo "[minio-init] Creating bucket ${MINIO_BUCKET_NAME} if it does not exist..."
/usr/bin/mc mb --ignore-existing "pfa-local/${MINIO_BUCKET_NAME}" >/dev/null

echo "[minio-init] Bucket initialization complete."
