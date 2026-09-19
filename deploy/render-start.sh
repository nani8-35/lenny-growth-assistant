#!/bin/sh
set -eu
(cd /agent && HOST=127.0.0.1 PORT=3001 node src/server.mjs) &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
