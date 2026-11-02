# -*- coding: utf-8 -*-
"""Push the working tree to GitHub without putting the token in argv, the remote
URL, git config on disk, or any file.

The credential travels as a one-shot ``http.extraheader`` supplied through git's
``GIT_CONFIG_*`` environment mechanism (git >= 2.31).
"""
import base64
import os
import subprocess
import sys
import winreg

NAME = "Github_personal_access_token_1"
LOGIN = os.environ.get("GH_REPO_OWNER", "Azhang2024-dev")
REPO = "conclusion-wordcount"
CWD = os.path.dirname(os.path.abspath(__file__))


def read_token() -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        for i in range(winreg.QueryInfoKey(k)[1]):
            n, v, _t = winreg.EnumValue(k, i)
            if n.lower() == NAME.lower():
                return v
    return ""


def main() -> int:
    token = read_token()
    if not token:
        print("token not found in HKCU\\Environment")
        return 1

    basic = base64.b64encode(("x-access-token:" + token).encode()).decode()
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.extraheader",
        "GIT_CONFIG_VALUE_0": "Authorization: Basic " + basic,
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "never",
    })

    def run(*args, **kw):
        return subprocess.run(["git"] + list(args), cwd=CWD, env=env,
                              capture_output=True, text=True, timeout=120, **kw)

    url = "https://github.com/%s/%s.git" % (LOGIN, REPO)
    print("remote:", url)
    if run("remote", "get-url", "origin").returncode != 0:
        run("remote", "add", "origin", url)

    r = run("push", "-u", "origin", "main")
    ok = r.returncode == 0
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.splitlines():
        if token in line:
            line = line.replace(token, "<redacted>")
        print("  ", line[:200])
    print("push rc:", r.returncode)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
