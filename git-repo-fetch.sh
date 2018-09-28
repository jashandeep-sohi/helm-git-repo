#!/bin/sh

. "$HELM_PLUGIN_DIR/venv/bin/activate"

python "$HELM_PLUGIN_DIR/git_repo.py" fetch "$@"

deactivate
