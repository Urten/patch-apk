#!/usr/bin/env python3
import argparse, os, sys, tempfile, shutil, subprocess
from pathlib import Path

from APK import APK
from ADBHelper import ADBHelper, ADBError

from termcolor import colored # pip3 install termcolor
from FridaGadget import FridaGadget

def abort(msg):
    print(colored(msg, "red"))
    sys.exit(1)

def warningPrint(msg):
    print(colored(msg, "yellow"))

def sign_with_apksigner(apk_path: str, verbose: bool = False):

    DEBUG_KS_NAME  = "patchapk.jks"
    DEBUG_KS_ALIAS = "patchapk"
    DEBUG_KS_PASS  = "patchapk" 
    script_dir = os.path.dirname(os.path.realpath(__file__))
    ks_path = os.path.join(script_dir, DEBUG_KS_NAME)
    cmd = [
        "apksigner", "sign",
        "--ks", ks_path,
        "--ks-key-alias", DEBUG_KS_ALIAS,
        "--ks-pass", f"pass:{DEBUG_KS_PASS}",
        "--key-pass", f"pass:{DEBUG_KS_PASS}",
        "--ks-type", "JKS",
        "--v1-signing-enabled=false",
        "--v2-signing-enabled=true",
        "--v3-signing-enabled=true",
        "--v4-signing-enabled=false",
        apk_path,
    ]
    if verbose:
        print("[apksigner] ", " ".join(cmd))
    cp = subprocess.run(cmd, check=True)
    
    

def choose_package(adb: ADBHelper, pattern: str, verbose: bool = False) -> str:
    matches = adb.get_packages(pattern)
    if not matches:
        raise abort(f"No packages found matching '{pattern}'")

    if len(matches) == 1:
        return matches[0]

    # Multiple matches: show menu, ask user to choose by number
    print("[*] Multiple matching packages found. Select the package to patch:")
    for i, name in enumerate(matches, start=1):
        print(f"[{i}] {name}")

    while True:
        try:
            choice = input("\nChoice (number, or 'q' to cancel): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raise ADBError("Selection cancelled.")

        if choice in ("q", "quit", "exit"):
            raise ADBError("Selection cancelled by user.")

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(matches):
                selected = matches[idx - 1]
                return selected

        print("Invalid choice. Please enter a number from the list, or 'q' to cancel.")


def main():
    ap = argparse.ArgumentParser(description="Pull, merge/patch, add gadget, build, align, sign, install.")
    ap.add_argument("pkg_pattern", help="Package name or substring")
    ap.add_argument("--serial", help="adb -s <serial>")
    ap.add_argument("--user", default="0", help="Preferred user id (fallback to others if not found)")
    ap.add_argument("--gadget-version", default=None, help="Frida Gadget version (None = latest)")
    ap.add_argument("--enable-user-certs", action="store_true", default=False,
                    help="Enable user-installed CA certs via networkSecurityConfig")
    ap.add_argument("--no-gadget", action="store_true", default=False,
                    help="Do not add Frida Gadget")
    ap.add_argument("--extract-only", action="store_true", default=False,
                    help="Only extract, merge and rebuild")
    ap.add_argument("--disable-styles-hack", action="store_true", default=False,
                    help="Skip duplicate <style><item> removal (merge step)")
    ap.add_argument("--no-install", action="store_true", help="Do not install to device at the end")
    ap.add_argument("--save-apk", help="Copy final APK to this path")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    adb = ADBHelper(serial=args.serial, verbose=args.verbose)
    pkg = choose_package(adb, args.pkg_pattern, verbose=args.verbose)

    print(f"[+] Using package: {colored(pkg, 'green')}")

    resolved_user, apk_paths = adb.get_apk_paths(pkg, user=args.user)

    if not apk_paths:
        raise ADBError(f"No APK paths found for {pkg}")
    
    if not args.extract_only:
        print("[+] Fetching Frida gadgets")
        gadget_version = FridaGadget(verbose = args.verbose).obtain_gadgets(args.gadget_version)
        if not args.gadget_version:
            warningPrint(f"No Frida Gadget version specified; using latest available ({gadget_version}).")
            warningPrint("Specify --gadget-version 16.7.19 for compatibility with objection")

    if args.verbose:
        print(f"[*] Resolved user: {resolved_user}")
        print(f"[*] APK paths: {apk_paths}")

    with tempfile.TemporaryDirectory(prefix="patchapk_") as tmp:
        # Pull split(s) via ADBHelper
        local_apks = adb.pull_files(apk_paths, tmp, pkg)

        
        print(f"[*] Pulled {len(local_apks)} APK(s)")
        for p in local_apks:
            print(f"    - {os.path.basename(p)}")

        if len(local_apks) == 1:
            print("[*] Single APK detected")
            base = APK(local_apks[0], verbose=args.verbose)
        else:
            print(f"[*] Split APK set detected ({len(local_apks)})")
            apks = [APK(p, verbose=args.verbose) for p in local_apks]

            # Find base APK (heuristic: filename containing "base", else first)
            base = next((p for p in apks if "base.apk" in p.apk_path), apks[0])
            others = [p for p in apks if p != base]
            base.merge_with(others, disable_styles_hack=args.disable_styles_hack)


        if len(local_apks) == 1:
            # If there's only one APK, and extract-only is requested, just copy it and exit
            if args.extract_only:
                target = args.save_apk if args.save_apk else f"{pkg}.apk"
                Path(os.path.dirname(target) or ".").mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local_apks[0], target)
                print(f"[+] Saved APK: {colored(target, 'green')}")
                return
        
            # Otherwise, disassemble it for patching
            base.disassemble()

        # Apply patches
        base.apply_patches(version=gadget_version,
                            enable_user_certs=args.enable_user_certs,
                            frida_gadget=not args.no_gadget)
        # Build final APK
        base.assemble()

        # If extract-only, save and exit
        if args.extract_only:
            target = args.save_apk if args.save_apk else f"{pkg}.apk"
            Path(os.path.dirname(target) or ".").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(final_apk, target)
            print(f"[+] Saved APK: {colored(target, 'green')}")
            return

        # Prep apk for installation
        base.zipalign(in_place=True)
        final_apk = base.apk_path

        # Sign
        print("[+] Signing with apksigner")
        sign_with_apksigner(final_apk, verbose=args.verbose)

        # Save copy if requested
        if args.save_apk or args.no_install:
            target = args.save_apk if args.save_apk else f"{pkg}.apk"
            Path(os.path.dirname(target) or ".").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(final_apk, target)
            print(f"[+] Saved APK: {colored(target, 'green')}")


        # Install via ADBHelper
        if not args.no_install:

            print(f"[+] Uninstalling original (user {resolved_user})")
            adb.uninstall_pkg(pkg, user=resolved_user)
            
            print(f"[+] Installing patched version (user {resolved_user})")
            adb.install_apk(final_apk, user=resolved_user, replace=True)


if __name__ == "__main__":
    try:
        main()
    except ADBError as e:
        print(f"[ADB ERROR] {e}", file=sys.stderr)
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print(f"[PROC ERROR] {e}", file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        sys.exit(130)
