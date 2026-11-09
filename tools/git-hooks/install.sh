#!/bin/sh
# Installs the versioned git guards (core.hooksPath, hook modes, local excludes).
cd "$(git rev-parse --show-toplevel)" && exec python3 tools/guards/check.py install "$@"
