"""Subprocess execution shared by build modules."""
import shlex
import subprocess


def execute(args, *, cwd=None, env=None, capture=False):
    args = [str(arg) for arg in args]
    print("+ " + shlex.join(args), flush=True)
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout
