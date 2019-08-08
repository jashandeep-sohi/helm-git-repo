#!/bin/sh

python -m venv --clear $HELM_PLUGIN_DIR/venv

source "$HELM_PLUGIN_DIR/venv/bin/activate"

pip install --upgrade pip
pip install -r $HELM_PLUGIN_DIR/requirements.txt
pip install -e $HELM_PLUGIN_DIR/.

deactivate
