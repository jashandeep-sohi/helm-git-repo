#!/bin/sh

source "$HELM_PLUGIN_DIR/venv/bin/activate"

export PYTHONPATH=$HELM_PLUGIN_DIR:$PYTHONPATH

python -m git_repo "$@"

deactivate
