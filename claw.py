"""
claw.py - OpenClaw Context Archive builder

A small utility that packages a directory into a .claw archive.
A .claw file is just a zip with a standardized structure:
  - manifest.json  (auto-generated metadata)
  - README.md      (auto-generated human explanation)
  - claw.py        (copy of this script, for portability)
  - context/       (whatever context files exist in the source)

Usage:
  python claw.py export <source_dir> [output_path]
  python claw.py import <claw_file> [target_dir]
  python claw.py info   <claw_file>
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone


FORMAT_NAME = "openclaw-context"
FORMAT_VERSION = "0.1"

GENERATED_SKILL = """\
# OpenClaw Context Archive Skill

You are working with an OpenClaw Context Archive (.claw file).

## What this is

This directory was extracted from a .claw archive. It contains agent session
context — conversation traces, scratch notes, working memory, and other
cognitive state from a previous session. This is NOT a database. It is a
continuation artifact meant to help you resume work.

## How to use this context

1. Read manifest.json to understand what files are present.
2. Look through context/ for any conversation history, scratch notes,
   tool logs, or working state from the previous session.
3. Use this context to orient yourself and continue the work that was
   in progress.

## How to export your context when done

When you are asked to export or save your context, run:

```
python claw.py export <this_directory> <output_name>.claw
```

This will:
- Regenerate manifest.json with current metadata
- Regenerate README.md
- Bundle everything in context/ into a portable .claw archive
- Include a copy of claw.py in the archive for portability

Then move the resulting .claw file to a mounted drive or shared location
so your human operator can retrieve it.

## Important

- Do NOT put database dumps or credentials in context/.
- This archive is for cognitive continuity, not authoritative data.
- Re-importing does not guarantee identical future outputs.
- The .claw format is just a zip file with standardized structure.
"""

GENERATED_README = """\
# OpenClaw Context Archive

This archive contains an OpenClaw agent context snapshot.

- It is **not** a database dump.
- It is **not** guaranteed to produce deterministic results.
- It is intended for session continuation and analysis.
- It is a portable, inspectable, non-authoritative cognitive checkpoint.

## Contents

- `manifest.json` — Machine-readable metadata about this archive.
- `README.md` — This file.
- `SKILL.md` — Instructions for the AI agent on how to use and re-export this context.
- `claw.py` — The utility used to generate this archive. Run it to re-export.
- `context/` — Agent working context (conversation traces, scratch, etc.)

## How to use

**Import into an agent runtime:**
```
python claw.py import this_file.claw /app/context
```

**Export updated context:**
```
python claw.py export /app/context output.claw
```

## Format

OpenClaw Context Archive Specification v{version}

This is a standard zip file with a `.claw` extension.
Anyone can unzip and inspect it.
""".format(version=FORMAT_VERSION)


def generate_manifest(source_dir):
    """Generate a fresh manifest.json for the archive."""
    context_files = []
    context_dir = os.path.join(source_dir, "context")
    if os.path.isdir(context_dir):
        for root, dirs, files in os.walk(context_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), source_dir)
                context_files.append(rel.replace("\\", "/"))

    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "claw.py",
        "context_files": context_files,
    }


def cmd_export(args):
    """Export a directory as a .claw archive."""
    source_dir = os.path.abspath(args.source_dir)
    if not os.path.isdir(source_dir):
        print(f"Error: source directory does not exist: {source_dir}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        basename = os.path.basename(source_dir)
        output_path = os.path.abspath(f"{basename}.claw")

    # Ensure .claw extension
    if not output_path.endswith(".claw"):
        output_path += ".claw"

    # Build archive in a temp directory to avoid including stale manifests
    with tempfile.TemporaryDirectory() as tmp:
        archive_root = os.path.join(tmp, "archive")
        os.makedirs(archive_root)

        # Copy context/ directory if it exists
        context_src = os.path.join(source_dir, "context")
        if os.path.isdir(context_src):
            shutil.copytree(context_src, os.path.join(archive_root, "context"))
        else:
            # Also support exporting the source dir itself as context
            # if there's no context/ subdirectory
            os.makedirs(os.path.join(archive_root, "context"))
            for item in os.listdir(source_dir):
                # Skip root-level generated files — we regenerate them
                if item in ("manifest.json", "README.md", "claw.py", "SKILL.md"):
                    continue
                src = os.path.join(source_dir, item)
                dst = os.path.join(archive_root, "context", item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        # Generate fresh manifest
        manifest = generate_manifest(archive_root)
        with open(os.path.join(archive_root, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Generate fresh README
        with open(os.path.join(archive_root, "README.md"), "w", encoding="utf-8") as f:
            f.write(GENERATED_README)

        # Generate skill file (agent instructions)
        with open(os.path.join(archive_root, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(GENERATED_SKILL)

        # Copy this script into the archive (self-inclusion for portability)
        this_script = os.path.abspath(__file__)
        shutil.copy2(this_script, os.path.join(archive_root, "claw.py"))

        # Create the zip
        zip_path = output_path
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(archive_root):
                for file in files:
                    full = os.path.join(root, file)
                    arcname = os.path.relpath(full, archive_root)
                    zf.write(full, arcname)

    print(f"Exported: {zip_path}")
    print(f"  format:  {FORMAT_NAME} v{FORMAT_VERSION}")
    print(f"  files:   {len(manifest['context_files'])} context file(s)")


def cmd_import(args):
    """Import a .claw archive into a target directory."""
    claw_file = os.path.abspath(args.claw_file)
    if not os.path.isfile(claw_file):
        print(f"Error: file not found: {claw_file}")
        sys.exit(1)

    target_dir = os.path.abspath(args.target_dir) if args.target_dir else os.getcwd()
    os.makedirs(target_dir, exist_ok=True)

    with zipfile.ZipFile(claw_file, "r") as zf:
        zf.extractall(target_dir)

    # Read and display manifest
    manifest_path = os.path.join(target_dir, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"Imported: {claw_file}")
        print(f"  format:  {manifest.get('format', '?')} v{manifest.get('version', '?')}")
        print(f"  created: {manifest.get('created_at', '?')}")
        print(f"  files:   {len(manifest.get('context_files', []))} context file(s)")
        print(f"  into:    {target_dir}")
    else:
        print(f"Imported: {claw_file} -> {target_dir}")
        print("  Warning: no manifest.json found in archive")


def cmd_info(args):
    """Display metadata from a .claw archive without extracting."""
    claw_file = os.path.abspath(args.claw_file)
    if not os.path.isfile(claw_file):
        print(f"Error: file not found: {claw_file}")
        sys.exit(1)

    with zipfile.ZipFile(claw_file, "r") as zf:
        names = zf.namelist()
        print(f"Archive: {claw_file}")
        print(f"  entries: {len(names)}")

        if "manifest.json" in names:
            with zf.open("manifest.json") as mf:
                manifest = json.load(mf)
            print(f"  format:  {manifest.get('format', '?')} v{manifest.get('version', '?')}")
            print(f"  created: {manifest.get('created_at', '?')}")
            print(f"  files:   {len(manifest.get('context_files', []))} context file(s)")
            print(f"  generator: {manifest.get('generated_by', '?')}")
        else:
            print("  Warning: no manifest.json")

        print("\nContents:")
        for name in sorted(names):
            info = zf.getinfo(name)
            print(f"  {name}  ({info.file_size} bytes)")


def main():
    parser = argparse.ArgumentParser(
        description="claw.py — OpenClaw Context Archive utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # export
    p_export = sub.add_parser("export", help="Export a directory as a .claw archive")
    p_export.add_argument("source_dir", help="Directory to package")
    p_export.add_argument("output", nargs="?", help="Output .claw file path (default: <dirname>.claw)")

    # import
    p_import = sub.add_parser("import", help="Import a .claw archive into a directory")
    p_import.add_argument("claw_file", help="The .claw file to import")
    p_import.add_argument("target_dir", nargs="?", help="Target directory (default: current dir)")

    # info
    p_info = sub.add_parser("info", help="Show metadata from a .claw archive")
    p_info.add_argument("claw_file", help="The .claw file to inspect")

    args = parser.parse_args()

    if args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "info":
        cmd_info(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
