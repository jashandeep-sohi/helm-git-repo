-------------
helm-git-repo
-------------
Helm plugin to use Git as a chart repository


Requirements
------------
- Helm >= 2.14.3 (might work with older 2.x versions)
- Python >= 3.7 (might work with older 3.x version)
- pip
- Git

Installation
------------
Install the latest development version::

  $ helm plugin install https://github.com/jashandeep-sohi/helm-git-repo

Usage
-----
::

  $ helm git-repo --help
  Usage: helm git-repo [OPTIONS] COMMAND [ARGS]...

  Options:
    --log-level [critical|error|warning|info|debug]
                                    Log level  [default: critical]
    --help                          Show this message and exit.

  Commands:
    add    Add a Git chart repository.
    index  Generate an index file from chart directories.


Add
===
To add a Git chart repository compatible with this plugin, use the ``add``
subcommand::

  $ helm git-repo add --help
  Usage: helm git-repo add [OPTIONS] NAME GIT_URL

    Add a chart repository.

  Options:
    --branch TEXT      [default: master]
    --index-path TEXT  [default: index.yaml]
    --help             Show this message and exit.

For example::

  $ helm git-repo add test 'https://github.com/jashandeep-sohi/charts.git' --index-path=stable/index.yaml

Now you can fetch/inspect/install/etc charts from this repo using the usual
commands::

  $ helm fetch test/prometheus
  $ helm inspect test/prometheus
  $ helm install test/prometheus


Index
=====
To create a Git chart repository compatible with this plugin, you'll need to
index it using::

  $ helm git-repo index --help
  Usage: helm git-repo index [OPTIONS] [CHART_DIRS]...

    Generate an index file from chart directories.

  Options:
    --out FILENAME                  File to write the index to  [default: -]
    --merge FILE                    Merge the generated index from the given
                                    index
    --skip-prompt / --no-skip-prompt
    --help                          Show this message and exit.


Let's use a fork of the official helm charts as an example::

  $ git clone 'https://github.com/jashandeep-sohi/charts.git' charts
  $ cd charts/

To index the chart in ``stable/prometheus`` directory::

  $ helm git-repo index stable/prometheus --out stable/index.yaml

You can also pass in multiple chart directories::

  $ helm git-repo index stable/prometheus stable/rethinkdb --out stable/index.yaml

Or, if you like, you can also build up the index incrementally::

  $ helm git-repo index stable/rethinkdb --out stable/index.yaml --merge stable/index.yaml

**Note:** ``helm git-repo index`` must be called from a Git working directory.
Also, it will use chart files from the **latest** commit to generate the index,
so please be sure to commit any chart changes before generating the index.

Next you'll want to publish the index by commiting & pushing it out::

  $ git add stable/index.yaml
  $ git commit ...
  $ git push ...

Now this this chart repository can be added with ``helm git-repo add ...``
