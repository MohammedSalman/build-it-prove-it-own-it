"""What runs where, and how to stop it.

    python ops/status.py                 # every environment: release, pid, health
    python ops/status.py --history       # ... plus every deploy and rollback so far
    python ops/status.py --stop all      # stop every server this kit started
    python ops/status.py --stop staging  # stop one
"""

import argparse

from envs import env_config, health, load_pipeline, load_state, port_in_use, stop


def show(history: bool) -> None:
    print(f"{'environment':<12} {'port':<6} {'release':<9} {'pid':<8} health")
    for name in load_pipeline()["environments"]:
        state = load_state(name)
        answer = health(name)
        if answer:
            line = f"ok, release {answer.get('release')}"
            release, pid = answer.get("release"), answer.get("pid")
        else:
            line = ("NOT ANSWERING, but its port is in use: python ops/status.py --stop "
                    f"{name}" if port_in_use(env_config(name)["port"]) else "not running")
            release = f"({state['release']})" if state.get("release") else "-"
            pid = state.get("spawned_pid") or "-"
        print(f"{name:<12} {env_config(name)['port']:<6} {release:<9} {str(pid):<8} {line}")
        if history:
            for h in state.get("history", []):
                extra = f"  ({h['reason']})" if h.get("reason") else ""
                print(f"{'':<12} {h['time']}  {h['action']:<8} {h['release']:<7} {h['result']}{extra}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stop", metavar="ENV", help="an environment name, or 'all'")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    if args.stop:
        names = list(load_pipeline()["environments"]) if args.stop == "all" else [args.stop]
        for name in names:
            print(f"{name}: {stop(name)}")
    else:
        show(args.history)


if __name__ == "__main__":
    main()
