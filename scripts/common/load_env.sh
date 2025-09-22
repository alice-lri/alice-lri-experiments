#!/usr/bin/env bash

dir="$(pwd)"
while [ "$dir" != "/" ]; do
  if [ -f "$dir/.env" ]; then
    export PROJECT_ROOT="$dir"
    set -o allexport
    source "$dir/.env"
    set +o allexport
    echo "Loaded environment variables from $dir/.env"
    return 0 2>/dev/null || exit 0
  fi
  dir="$(dirname "$dir")"
done

echo "Error: .env not found in this directory tree." >&2
return 1 2>/dev/null || exit 1
