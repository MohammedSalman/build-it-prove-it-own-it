"""Environments: where each one lives, what runs there, and how to start and stop it.

An environment is a name from ops/pipeline.json (staging, production, restore) with its
own port, its own database file (envs/<name>/afterhours.db) and its own flag file.
Only the standard library is used, so this runs the same on macOS, Linux and Windows.
"""

import errno
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
RELEASES = KIT / "releases"
ENVS = KIT / "envs"
BACKUPS = KIT / "backups"

# Talk to 127.0.0.1 directly, even if the shell has an HTTP proxy configured.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# ---------- configuration ----------

def load_pipeline() -> dict:
    return json.loads((KIT / "ops" / "pipeline.json").read_text(encoding="utf-8-sig"))


def env_config(name: str) -> dict:
    envs = load_pipeline()["environments"]
    if name not in envs:
        sys.exit(f"Unknown environment '{name}'. Known: {', '.join(envs)}.")
    return envs[name]


def base_url(name: str) -> str:
    return f"http://127.0.0.1:{env_config(name)['port']}"


def env_dir(name: str) -> Path:
    path = ENVS / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path(name: str) -> Path:
    return env_dir(name) / "afterhours.db"


def release_dir(release: str) -> Path:
    path = RELEASES / release
    if not (path / "app" / "main.py").exists():
        known = ", ".join(sorted(p.name for p in RELEASES.iterdir() if p.is_dir()))
        sys.exit(f"There is no release '{release}' in releases/. Known: {known}.")
    return path


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- state: what runs where, and what happened before ----------

def load_state(name: str) -> dict:
    path = env_dir(name) / "state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"release": None, "pid": None, "history": []}


def save_state(name: str, state: dict) -> None:
    text = json.dumps(state, indent=2) + "\n"
    (env_dir(name) / "state.json").write_text(text, encoding="utf-8")


def record(name: str, action: str, release: str, result: str, **extra) -> None:
    state = load_state(name)
    state["history"].append({"time": now(), "action": action, "release": release,
                             "result": result, **extra})
    save_state(name, state)


def last_good(name: str, exclude: str | None) -> str | None:
    """The most recent release that passed its gates here, other than `exclude`."""
    for entry in reversed(load_state(name)["history"]):
        if entry["result"] == "ok" and entry["release"] != exclude:
            return entry["release"]
    return None


# ---------- HTTP ----------

def http(method: str, url: str, body: dict | None = None, timeout: float = 5.0):
    """Send one request. Returns (status, body, seconds).

    status is None when there was no answer at all (refused, reset, timed out).
    body is parsed JSON when possible, otherwise text.
    """
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with _opener.open(req, timeout=timeout) as res:
            status, raw = res.status, res.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    except (OSError, HTTPException) as err:
        return None, str(getattr(err, "reason", err)), time.perf_counter() - started
    seconds = time.perf_counter() - started
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = raw.decode("utf-8", "replace")
    return status, parsed, seconds


def health(name: str, timeout: float = 2.0) -> dict | None:
    """The environment's GET /healthz answer, or None if it does not answer 200."""
    status, body, _ = http("GET", base_url(name) + "/healthz", timeout=timeout)
    return body if status == 200 and isinstance(body, dict) else None


def port_in_use(port: int) -> bool:
    """True unless the port clearly refuses connections.

    A port counts as in use when something accepts the connection, and also when the
    attempt just times out: a frozen server still holds its port. The timeout is generous
    because Windows takes a second or two to refuse a connection on 127.0.0.1.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(3.0)
        code = s.connect_ex(("127.0.0.1", port))
    return code not in (errno.ECONNREFUSED, getattr(errno, "WSAECONNREFUSED", 10061))


# ---------- starting and stopping servers ----------
#
# start() launches each server in a session (macOS/Linux) or process group (Windows) of its
# own and records the launched process id as "spawned_pid" in state.json before waiting for
# it, so a server that never becomes healthy can still be found and stopped. A running server
# also reports its own process id in /healthz. On Windows the venv's python.exe is a small
# launcher that starts the real interpreter as a child, so the two ids differ there; ending
# the whole process tree covers both.

def _end_tree(pid: int, force: bool = False) -> None:
    """End process `pid` and its children. Only used on servers this kit started."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(pid, sig)          # the server leads its own process group
    except ProcessLookupError:
        try:
            os.kill(pid, sig)        # started some other way: end just that process
        except ProcessLookupError:
            pass


_CHILDREN: dict[int, subprocess.Popen] = {}   # servers started by this Python process


def _alive(pid: int) -> bool:
    """Is process `pid` still running? (Standard library only, on every platform.)"""
    if pid in _CHILDREN:                    # our own child: poll() also reaps it once it ends
        return _CHILDREN[pid].poll() is None
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259                           # STILL_ACTIVE
    try:
        os.kill(pid, 0)                                    # signal 0: only asks, sends nothing
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_gone(pid: int, port: int, seconds: float) -> bool:
    """Wait until the process has ended and its port refuses connections."""
    deadline = time.monotonic() + seconds
    while _alive(pid) or port_in_use(port):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.2)
    return True


def _forget_process(name: str) -> None:
    state = load_state(name)
    state["pid"] = None
    state["spawned_pid"] = None
    save_state(name, state)


def stop(name: str) -> str:
    """Stop the AfterHours server of this environment, healthy or not. Returns what happened."""
    port = env_config(name)["port"]
    spawned = load_state(name).get("spawned_pid")
    answer = health(name)
    if answer is None and not port_in_use(port):
        _forget_process(name)
        return "nothing was running"
    if answer is not None:
        pid, what = int(answer["pid"]), f"{answer.get('release')} (pid {answer['pid']})"
    elif spawned:
        pid, what = int(spawned), f"a server that did not answer /healthz (pid {spawned})"
    else:
        sys.exit(f"Port {port} ({name}) is in use, but it does not answer like AfterHours and this\n"
                 f"kit did not start it. Stop that program, or give {name} another port in\n"
                 f"ops/pipeline.json.")
    _end_tree(pid)
    if not _wait_gone(pid, port, 15):
        _end_tree(pid, force=True)
        if not _wait_gone(pid, port, 5):
            sys.exit(f"The {name} server (pid {pid}) did not stop. Stop it by hand:\n"
                     f"  macOS/Linux: kill -9 {pid}      PowerShell: Stop-Process -Force -Id {pid}")
    _forget_process(name)
    return f"stopped {what}"


def start(name: str, release: str) -> tuple[dict | None, str]:
    """Start `release` for this environment and wait until /healthz answers.

    Returns (health answer, "") on success, or (None, what went wrong). A server that does
    not become healthy is stopped again before this returns.
    """
    config = env_config(name)
    port = config["port"]
    folder = release_dir(release)
    if port_in_use(port):
        return None, f"port {port} is still in use"

    env = {k: v for k, v in os.environ.items() if not k.startswith("AFTERHOURS_")}
    env.update({
        "AFTERHOURS_DB": str(db_path(name)),
        "AFTERHOURS_FLAGS": str(KIT / config["flags"]),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    log_path = env_dir(name) / "server.log"
    with open(log_path, "ab") as log:
        log.write(f"\n--- {now()} starting {release} on port {port}\n".encode())
        log.flush()
        if os.name == "nt":
            detach = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
                      | subprocess.DETACHED_PROCESS}
        else:
            detach = {"start_new_session": True}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, **detach)
    _CHILDREN[proc.pid] = proc
    state = load_state(name)
    state.update({"spawned_pid": proc.pid, "pid": None})
    save_state(name, state)

    def give_up(reason: str) -> tuple[None, str]:
        _end_tree(proc.pid)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _end_tree(proc.pid, force=True)
            proc.wait(timeout=10)
        _wait_gone(proc.pid, port, 10)
        _forget_process(name)
        return None, reason

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return give_up(f"{release} exited during start-up (exit code {proc.returncode}); "
                           f"see envs/{name}/server.log")
        answer = health(name, timeout=1.0)
        if answer is not None:
            if answer.get("release") != release:
                return give_up(f"port {port} answers as release {answer.get('release')}, "
                               f"not {release}")
            state = load_state(name)
            state.update({"release": release, "pid": answer["pid"], "port": port,
                          "started_at": now()})
            save_state(name, state)
            return answer, ""
        time.sleep(0.2)
    return give_up(f"{release} did not answer /healthz within 30 s and was stopped; "
                   f"see envs/{name}/server.log")


def switch(name: str, release: str) -> tuple[dict | None, str, str]:
    """Stop what runs now and start `release`. Returns (health, error, what was stopped)."""
    stopped = stop(name)
    answer, error = start(name, release)
    return answer, error, stopped


def step(number: str, label: str, ok: bool | None, detail: str) -> None:
    mark = {True: "ok", False: "FAIL", None: "--"}[ok]
    print(f"  [{number}] {label:<10} {mark:<5} {detail}")
