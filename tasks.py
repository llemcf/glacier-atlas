# coding=utf-8
import os

# from deepki.invokator.install import write_netrc_from_s3
from invoke import task


@task
def clean(ctx):
    ctx.run("rm -rf build dist *.egg-info htmlcov")
    ctx.run('find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf')


@task
def pip_install(ctx):
    ctx.run("pip install --quiet -r <(cat requirements.txt)")


@task(clean, pip_install)
def test(ctx):
    ctx.run("py.test tests/")


@task(clean, pip_install)
def build(ctx):
    """
    runs setup.py build
    """
    ctx.run("python setup.py build")
    ctx.run("python setup.py sdist")
    ctx.run("python setup.py egg_info")


# @task
# def write_netrc(ctx):
#     """Write  ~/.netrc file from s3 credentials"""
#     write_netrc_from_s3(ctx)


@task
def docker_login(ctx, aws_profile, registry):
    ctx.run(
        f"aws ecr get-login-password --profile {aws_profile} | "
        f"docker login --username AWS --password-stdin {registry}"
    )


@task
def get_project_version(ctx):
    ctx.run("poetry version --short")


@task
def get_poetry_version(ctx):
    ctx.run("poetry about -V | grep -Eo '[0-9]+(\.[0-9]+)+'")


@task
def get_prefect_version(ctx):
    ctx.run("poetry show prefect | awk '/version/ { print $3 }'")


@task
def prefect_deploy(ctx):
    ctx.run(f"prefect --no-prompt deploy")
