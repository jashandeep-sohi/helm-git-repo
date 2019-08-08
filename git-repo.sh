#!/bin/sh

source "$HELM_PLUGIN_DIR/venv/bin/activate"

python -m git_repo "$@"

deactivate
