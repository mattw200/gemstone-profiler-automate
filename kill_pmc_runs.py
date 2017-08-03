#!/usr/bin/env python

# Matthew J. Walker
# Created: 02 August 2017

def kill_all_pmc_runs():
    import os, subprocess, signal
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    for line in out.splitlines():
        if './bin/pmc-run' in line:
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)


if __name__ == "__main__":
    kill_all_pmc_runs()
