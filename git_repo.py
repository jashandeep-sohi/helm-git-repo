import click
import pathlib
import tempfile
import subprocess
import sys
import urllib.parse
import hashlib
import logging

from os import getenv


logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--log-level",
    help="Log level",
    type=click.Choice(["critical", "error", "warning", "info", "debug"]),
    default="info",
    show_default=True,
)
def cli(log_level):
    handler = ClickLoggingHandler()
    handler.setFormatter(ClickLoggingFormatter())
    logger.addHandler(handler)
    logger.setLevel(log_level.upper())

    if getenv("HELM_DEBUG") == "1":
        logger.setLevel(logging.DEBUG)


@cli.command(
    "add",
    short_help="add a chart repository"
)
@click.argument(
    "NAME"
)
@click.argument(
    "URL"
)
def add(name, url):
    


@cli.command(
    "index",
    short_help="Generate an index file from chart directories",
)
@click.argument(
    "CHART_DIRS",
    nargs=-1,
    type=click.Path(dir_okay=True, file_okay=False, exists=True),
)
@click.option(
    "--out",
    help="File to write the index to",
    type=click.File("w", atomic=True),
    default="-",
    show_default=True,
)
@click.option(
    "--merge",
    help="Merge the generated index into the given index",
    type=click.Path(dir_okay=False, file_okay=True, exists=True),
)
def index(chart_dirs, out, merge=None):
    """
    Generate an index file given a list of chart directories.
    """
    if not chart_dirs:
        exit(0)

    _, commit, _ = sh("git rev-parse --verify HEAD")
    _, git_root, _ = sh("git rev-parse --show-toplevel")

    sh("helm repo update", show=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = pathlib.Path(tmp_dir)

        if merge is None:
            merge = tmp_dir / "merge.yaml"

        for chart_dir in sorted(chart_dirs):
            chart_dir = pathlib.Path(chart_dir)

            sh(
                "git --work-tree='{!s}' checkout '{!s}' -- '{!s}'".format(
                    tmp_dir,
                    commit,
                    chart_dir
                )
            )

            tmp_chart_dir = tmp_dir / chart_dir

            sh(
                "helm dependency update --skip-refresh '{!s}'".format(
                    tmp_chart_dir
                )
            )

            sh(
                "helm package --destination '{!s}' '{!s}'".format(
                    tmp_chart_dir,
                    tmp_chart_dir,
                )
            )

            url = "?ref={!s}&path={!s}".format(commit, chart_dir)

            sh(
                "helm repo index --url '{!s}' --merge '{!s}' '{!s}'".format(
                    url,
                    merge,
                    tmp_chart_dir,
                )
            )

            merge = tmp_chart_dir / "index.yaml"

        with open(merge, "r") as index_fobj, out as out_fobj:
            out_fobj.writelines(index_fobj)

        exit(0, "Sucessfully wrote index to '{!s}'".format(out.name))


@cli.command("fetch")
@click.argument("cert_file")
@click.argument("key_file")
@click.argument("ca_file")
@click.argument("url")
def fetch(cert_file, key_file, ca_file, url):
    "Output the chart tarball or repo index to STDOUT."""
    logger.debug("input url %s", url)

    url = urllib.parse.urlparse(url)
    logger.debug(url)

    path = pathlib.PurePath(url.path)

    if path.name == "index.yaml":
        print_index(url)
    elif path.suffix == ".tgz":
        print_chart_tarball(url)
    else:
        exit(1, "Unable to handle: %s", path)


def print_index(url):
    git_url = url._replace(
        scheme=url.scheme.lstrip("git+"),
        path="",
        query="",
        fragment="",
    ).geturl()

    query = urllib.parse.parse_qs(url.query, strict_parsing=True)

    ref = query.get("ref", "master")

    plugin_home = pathlib.Path(getenv("HELM_PLUGIN_DIR"))

    repo_name = sha(git_url)

    git_dir = plugin_home / "store.git"

    git(git_dir, "init --bare '{!s}'".format(git_dir))

    git(git_dir, "remote add")

    git(git_dir, "fetch '{!s}' '{!s}'".format(repo_name, ref))


def print_chart_tarball(url):
    pass


def sha(utf8_data):
    return hashlib.sha256(utf8_data.encode("utf-8")).hexdigest()


def git(git_dir, cmd, *args, **kwargs):
    return sh(
        "git --git-dir '{!s}' {!s}".format(git_dir, cmd),
        *args,
        **kwargs
    )


def exit(ret, *args):
    if args:
        if ret != 0:
            logger.error(*args)
        else:
            logger.info(*args, extra=dict(click={"fg": "green"}))

    raise SystemExit(ret)


def click_log(level, msg, **kwargs):
    logger.log(level, msg, extra={"click": kwargs})


def sh(*args, show=False, hide_cmd=False, hide_out=False, hide_err=False,
       exit_on_error=True, **kwargs):
    proc = subprocess.Popen(
        *args,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs
    )

    cmd_level = logging.INFO if show and not hide_cmd else logging.DEBUG
    stdout_level = logging.INFO if show and not hide_out else logging.DEBUG
    stderr_level = logging.WARN if show and not hide_err else logging.DEBUG

    click_log(cmd_level, proc.args, bold=True)

    out, err = proc.communicate()
    ret = proc.returncode

    if out:
        out = out.decode("utf-8").strip()
        click_log(stdout_level, out)

    if err:
        err = err.decode("utf-8").strip()

    if exit_on_error and ret !=0:
        logger.error(err)
        raise SystemExit(ret)
    elif err:
        click_log(stderr_level, err)

    return ret, out, err


class ClickLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            click.secho(
                self.format(record),
                err=True,
                **getattr(record, "click", {})
            )
        except Exception:
            self.handleError(record)


class ClickLoggingFormatter(logging.Formatter):

    def format(self, record):
        fmt_by_level = {
            "error": dict(fg="red"),
            "exception": dict(fg="red"),
            "warning": dict(fg="orange"),
        }

        fmt = fmt_by_level.get(record.levelname.lower(), {})

        setattr(record, "click", {**getattr(record, "click", {}), **fmt})

        return super().format(record)


if __name__ == "__main__":
    cli.main(prog_name="helm git-repo")
