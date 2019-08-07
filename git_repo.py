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
        logger.setLevel("DEBUG")


@cli.command(
    "add"
)
@click.argument("NAME")
@click.argument("GIT_URL")
@click.option(
    "--branch",
    default="master",
    show_default=True,
)
@click.option(
    "--index-path",
    default="index.yaml",
    show_default=True,
)
def add(name, git_url, branch, index_path):
    """
    Add a chart repository.
    """
    url = "git-repo+index:{!s}?branch={!s}&index_path={!s}&name={!s}".format(
        git_url,
        branch,
        index_path,
        name
    )
    sh("helm repo add {!s} '{!s}'".format(name, url), show=True)


@cli.command(
    "index"
)
@click.argument(
    "CHART_DIRS",
    nargs=-1,
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
    help="Merge the generated index from the given index",
    type=click.Path(dir_okay=False, file_okay=True, exists=True),
    default=None
)
@click.option("--skip-prompt/--no-skip-prompt", default=False)
def index(chart_dirs, out, merge, skip_prompt):
    """
    Generate an index file from chart directories.
    """
    if not chart_dirs:
        exit(0)

    if not skip_prompt:
        _, git_log, _ = sh("git log -1")

        click.secho(git_log, fg="yellow", err=True)
        click.confirm(
            "Proceed with files from this commit?",
            default=True,
            abort=True,
            err=True
        )

    _, commit_ref, _ = sh("git log -1 --format='%H'")
    _, git_root, _ = sh("git rev-parse --show-toplevel")

    sh("helm repo update", show=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = pathlib.Path(tmp_dir)

        if merge is None:
            merge = tmp_dir / "merge.yaml"

        for chart_dir in chart_dirs:
            chart_dir = pathlib.Path(chart_dir).resolve().relative_to(git_root)

            sh(
                "git --work-tree='{!s}' checkout '{!s}' -- '{!s}'".format(
                    tmp_dir,
                    commit_ref,
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

            url = "git-repo+chart://{!s}/{!s}".format(
                commit_ref,
                chart_dir
            )

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


@cli.command("fetch", hidden=True)
@click.argument("cert_file")
@click.argument("key_file")
@click.argument("ca_file")
@click.argument("url")
def fetch(cert_file, key_file, ca_file, url):
    """
    Output a chart tarball or repo index to STDOUT.
    """

    logger.debug("input url %s", url)

    if url.startswith("git-repo+index"):
        print_index(url)
    elif url.startswith("git-repo+chart"):
        print_chart_tarball(url)
    else:
        exit(1, "Unable to handle {!s}".format(url))


def print_index(url):
    parsed_url = urllib.parse.urlparse(url)
    logger.debug("parsed url %r", parsed_url)

    git_url = parsed_url.path

    query_params = urllib.parse.parse_qs(parsed_url.query)
    logger.debug("parsed query params %r", query_params)

    repo_name = query_params.get("name", [None])[0]
    git_branch = query_params.get("branch", ["master"])[0]
    git_index_path = query_params.get("index_path", ["index.yaml"])[0]

    plugin_home = pathlib.Path(getenv("HELM_PLUGIN_DIR"))

    if not repo_name:
        exit(1, "invalid url; must set 'name=' query paramater")

    git_dir = plugin_home / "git" / repo_name

    if not git_dir.exists():
        git(git_dir, "init --bare '{!s}'".format(git_dir))
        git(git_dir, "remote add origin '{!s}'".format(git_url))

    git(
        git_dir,
        "fetch origin '{!s}:{!s}'".format(git_branch, git_branch),
    )

    _, out, _ = git(
        git_dir,
        "show '{!s}':'{!s}'".format(
            git_branch,
            git_index_path
        )
    )

    out = out.replace(
        "git-repo+chart://",
        "git-repo+chart://{!s}/".format(repo_name)
    )

    click.echo(out)


def print_chart_tarball(url):
    parsed_url = urllib.parse.urlparse(url)
    logger.debug("parsed url %r", parsed_url)

    repo_name = parsed_url.netloc
    path = pathlib.Path(parsed_url.path)

    commit_ref = path.parts[1]
    git_path = "/".join(path.parts[2:-1])

    logger.debug("repo_name: %s", repo_name)
    logger.debug("commit_ref: %s", commit_ref)
    logger.debug("git_path: %s", git_path)

    plugin_home = pathlib.Path(getenv("HELM_PLUGIN_DIR"))
    git_dir = plugin_home / "git" / repo_name

    git(
        git_dir,
        "fetch origin {!s}:{!s}".format(commit_ref, commit_ref),
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = pathlib.Path(tmp_dir)

        git(
            git_dir,
            "--work-tree='{!s}' checkout 'refs/heads/{!s}' -- '{!s}'".format(
                tmp_dir,
                commit_ref,
                git_path
            )
        )

        tmp_chart_dir = tmp_dir / git_path

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

        chart_tgz_loc = tmp_chart_dir / path.name

        chart_tgz_fobj = click.open_file(chart_tgz_loc, "rb")
        stdout_fobj = click.open_file("-", "wb")

        with chart_tgz_fobj as chart_tgz_fobj, stdout_fobj as stdout_fobj:
            stdout_fobj.writelines(chart_tgz_fobj)



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

    if exit_on_error and ret != 0:
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
            "warning": dict(fg="yellow"),
        }

        fmt = fmt_by_level.get(record.levelname.lower(), {})

        setattr(record, "click", {**getattr(record, "click", {}), **fmt})

        return super().format(record)


if __name__ == "__main__":
    cli.main(prog_name="helm git-repo")
