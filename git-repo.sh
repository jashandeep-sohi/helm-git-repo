#!/bin/sh

. "$HELM_PLUGIN_DIR/venv/bin/activate"

PYTHONPATH=$HELM_PLUGIN_DIR:$PYTHONPATH python -m git_repo "$@"

deactivate
