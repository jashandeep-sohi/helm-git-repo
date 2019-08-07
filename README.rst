-------------
helm-git-repo
-------------
Helm plugin to use Git as a chart repository


Requirements
------------
- Helm >= 2.14.3
- Python >= 3.7
- pip
- Git

Installation
------------
Install the latest version::

  $ helm plugin install https://github.com/jashandeep-sohi/helm-git-repo

Test if everything installed correctly::

  $ helm git-repo --help

Usage
-----
Assuming you have some charts commited to a Git repository, you'll first want
to generate an index file. Let's use a fork of the official helm charts::

  $ git clone 'https://github.com/jashandeep-sohi/charts.git' charts
  $ cd charts/
  $ helm git-repo index stable/prometheus --out stable/index.yaml

Next you'll want to publish the index by commiting it to the repo & pushing it
out::

  $ git add stable/index.yaml
  $ git commit ...
  $ git push ...

Now add this Git chart repository to Helm::

  $ helm git-repo add test 'https://github.com/jashandeep-sohi/charts.git' --index-path=stable/index.yaml

And that's it. Now you can fetch/inspect/install/etc charts from this repo
using the usual commands::

  $ helm fetch test/prometheus
  $ helm inspect test/prometheus
  $ helm install test/prometheus
