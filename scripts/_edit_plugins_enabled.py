#!/usr/bin/env python3
"""Add/remove one plugin id in a profile's `config.yaml` `plugins.enabled` list, as a
careful line-level text edit that preserves every other line/comment/formatting in the
file untouched (docs/ARCHITECTURE.md §8: install.sh must NOT use
`hermes config set plugins.enabled ...`, which stores a STRING, not a YAML list — see
the hermes-desktop-plugins SKILL's warning). Never reformats the whole file with a
YAML dump/round-trip (that would drop comments).

Usage: _edit_plugins_enabled.py <config.yaml> <plugin_id> add|remove
Exit codes: 0 = changed or already in the desired state; 1 = error (message on stderr).
Never partially writes: builds the new content in memory, then does one atomic
os.replace() over a temp file in the same directory.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

_TOP_KEY_RE = re.compile(r"^\S")  # a line starting at column 0 = a new top-level key
_PLUGINS_KEY_RE = re.compile(r"^plugins:\s*(#.*)?$")
_ENABLED_INLINE_RE = re.compile(r"^(\s*)enabled:\s*\[\s*\]\s*(#.*)?$")
_ENABLED_BLOCK_RE = re.compile(r"^(\s*)enabled:\s*(#.*)?$")
_LIST_ITEM_RE = re.compile(r"^(\s*)-\s*(.+?)\s*(#.*)?$")


def _item_matches(text: str, plugin_id: str) -> bool:
    text = text.strip().strip('"').strip("'")
    return text == plugin_id


def edit(lines: list[str], plugin_id: str, action: str) -> list[str]:
    # Locate the top-level `plugins:` block.
    start = None
    for i, line in enumerate(lines):
        if _PLUGINS_KEY_RE.match(line):
            start = i
            break
    if start is None:
        if action == "remove":
            return lines  # nothing to remove — already absent
        # No `plugins:` key at all: append a fresh block at the end of the file.
        new_lines = list(lines)
        if new_lines and new_lines[-1].strip() != "":
            new_lines.append("\n")
        new_lines.append("plugins:\n")
        new_lines.append("  enabled:\n")
        new_lines.append(f"    - {plugin_id}\n")
        return new_lines

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip() != "" and _TOP_KEY_RE.match(lines[i]):
            end = i
            break

    block = lines[start:end]

    # Inline empty list: `enabled: []`.
    for j, line in enumerate(block):
        m = _ENABLED_INLINE_RE.match(line)
        if m:
            indent = m.group(1)
            if action == "remove":
                return lines  # empty list already has nothing to remove
            new_block = block[:j] + [f"{indent}enabled:\n", f"{indent}  - {plugin_id}\n"] + block[j + 1:]
            return lines[:start] + new_block + lines[end:]

    # Block form: `enabled:` header followed by indented `- item` lines.
    for j, line in enumerate(block):
        m = _ENABLED_BLOCK_RE.match(line)
        if not m:
            continue
        header_indent = m.group(1)
        item_indent = None
        items_end = j + 1
        found_idx = None
        while items_end < len(block):
            item_line = block[items_end]
            im = _LIST_ITEM_RE.match(item_line)
            if not im or len(im.group(1)) <= len(header_indent):
                break
            if item_indent is None:
                item_indent = im.group(1)
            if _item_matches(im.group(2), plugin_id):
                found_idx = items_end
            items_end += 1

        if action == "remove":
            if found_idx is None:
                return lines  # already absent
            remaining_items = [
                b for k, b in enumerate(block[j + 1:items_end], start=j + 1) if k != found_idx
            ]
            if remaining_items:
                new_block = block[: j + 1] + remaining_items + block[items_end:]
            else:
                # Last remaining item removed: collapse back to an inline empty list rather
                # than leaving a bare `enabled:` header, which YAML parses as null, not [].
                new_block = block[:j] + [f"{header_indent}enabled: []\n"] + block[items_end:]
            return lines[:start] + new_block + lines[end:]

        # action == "add"
        if found_idx is not None:
            return lines  # already present, idempotent no-op
        insert_indent = item_indent if item_indent is not None else header_indent + "  "
        new_item = f"{insert_indent}- {plugin_id}\n"
        new_block = block[: j + 1] + [new_item] + block[j + 1:]
        return lines[:start] + new_block + lines[end:]

    # `plugins:` block exists but has no `enabled:` key at all.
    if action == "remove":
        return lines
    insert_at = 1  # right after the `plugins:` header line
    new_block = block[:insert_at] + ["  enabled:\n", f"    - {plugin_id}\n"] + block[insert_at:]
    return lines[:start] + new_block + lines[end:]


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[3] not in ("add", "remove"):
        print(__doc__, file=sys.stderr)
        return 1
    path, plugin_id, action = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.isfile(path):
        print(f"error: {path} does not exist", file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        original = f.readlines()

    updated = edit(original, plugin_id, action)
    if updated == original:
        print(f"no change needed ({action} {plugin_id!r} already reflected)")
        return 0

    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".config.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(updated)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    verb = "added" if action == "add" else "removed"
    print(f"{verb} {plugin_id!r} in plugins.enabled ({path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
