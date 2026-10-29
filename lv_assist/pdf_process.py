"""Bound renderer lifetime, including descendant processes owned by this attempt."""

import os
import signal
import subprocess


def run_pdf_process(args, *, timeout=120):
    options = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, args, stdout, stderr)
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    finally:
        if os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=10, check=False)
        if process.poll() is None:
            process.kill()
        process.communicate()
