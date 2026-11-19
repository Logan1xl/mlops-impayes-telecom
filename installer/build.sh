#!/bin/bash
# Construit les exécutables autonomes (Windows, Linux, macOS) de la démo.
# Usage : installer/build.sh
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHER="$REPO_ROOT/installer/launcher"
DEMO_DIST="$REPO_ROOT/demo/dist"

# 1. Copier la démo dans assets (ce que l'exécutable embarque)
cd "$LAUNCHER"
rm -rf assets
mkdir -p assets
cp -R "$REPO_ROOT/demo/index.html" assets/
cp -R "$REPO_ROOT/demo/assets" assets/
echo "✓ assets synchronisés : $(du -sh assets | cut -f1)"

# 1bis. Module Go (une seule fois)
if [ ! -f go.mod ]; then
  go mod init impayes-demo >/dev/null
  echo "✓ go.mod créé"
fi

# 2. Compiler pour les 3 OS
mkdir -p "$DEMO_DIST"
LDFLAGS="-s -w"
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="$LDFLAGS" -o "$DEMO_DIST/NaijaTel-ImpayesAI-Demo.exe" .
CGO_ENABLED=0 GOOS=linux   GOARCH=amd64 go build -ldflags="$LDFLAGS" -o "$DEMO_DIST/NaijaTel-ImpayesAI-Demo-linux" .
CGO_ENABLED=0 GOOS=darwin  GOARCH=arm64 go build -ldflags="$LDFLAGS" -o "$DEMO_DIST/NaijaTel-ImpayesAI-Demo-macos-arm64" .
CGO_ENABLED=0 GOOS=darwin  GOARCH=amd64 go build -ldflags="$LDFLAGS" -o "$DEMO_DIST/NaijaTel-ImpayesAI-Demo-macos-amd64" .
echo "✓ binaires construits dans $DEMO_DIST :"
ls -lh "$DEMO_DIST" | grep -v "^total"
