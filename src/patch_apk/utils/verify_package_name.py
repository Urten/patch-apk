import subprocess
from patch_apk.utils.cli_tools import abort
import os

def verifyPackageName(pkgname):
    # Get a list of installed packages matching the given name
    packages = []
    proc = subprocess.run(["adb", "shell", "pm", "list", "packages"], stdout=subprocess.PIPE)
    if proc.returncode != 0:
        abort("Error: Failed to run 'adb shell pm list packages'.")
    out = proc.stdout.decode("utf-8")
    for line in out.split(os.linesep):
        if line.startswith("package:"):
            line = line[8:].strip()
            if pkgname.lower() in line.lower():
                packages.append(line)