"""Import a preserved line-numbered public primary-source web capture.

This is an explicit acquisition adapter, not model-generated article text. It
retains the original tool outputs and exact line selection, rejects gaps and
conflicting overlaps, and never overwrites a source. The caller must identify
the article boundaries so platform recommendations are not imported as evidence.
"""
import argparse
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

from scripts.model_backend import atomic_json, digest


def import_capture(captures, destination, *, url, first, last, title):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Source destination must be empty")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTPS source URL without credentials is required")
    if first < 0 or last < first:
        raise ValueError("Invalid line selection")
    lines, originals = {}, []
    for path in map(Path, captures):
        raw = path.read_bytes()
        value = raw.decode("utf-8")
        if url not in value:
            raise ValueError("Capture does not identify the requested source URL")
        originals.append((path.name, raw))
        for line in value.splitlines():
            match = re.match(r"^L(\d+):(?: ?)(.*)$", line)
            if match and first <= int(match[1]) <= last:
                n, content = int(match[1]), match[2]
                if n in lines and lines[n] != content:
                    raise ValueError("Conflicting capture overlap")
                lines[n] = content
    if set(lines) != set(range(first, last + 1)):
        raise ValueError("Selected source lines have gaps")
    text = "\n".join(lines[n] for n in range(first, last + 1))
    normalize = lambda s: re.sub(r"\W+", "", s).lower()
    if len(text) < 500 or not normalize(title) or normalize(title) not in normalize(text):
        raise ValueError("Insufficient article text or title mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    provenance = []
    for index, (name, raw) in enumerate(originals):
        target = destination / f"capture_{index}.txt"
        target.write_bytes(raw)
        provenance.append({"original_name": name, "path": target.name,
                           "sha256": hashlib.sha256(raw).hexdigest()})
    doc = {"text": text, "sha256": digest(text), "url": url,
           "format": "preserved primary-source web capture", "parser_version": 2,
           "identity": {"title": title, "verification": "title present in selected primary text"},
           "capture_provenance": {"files": provenance, "first_line": first,
                                  "last_line": last, "selection": "inclusive contiguous source lines"}}
    atomic_json(destination / "text.json", doc)
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--first", type=int, required=True)
    parser.add_argument("--last", type=int, required=True)
    args = parser.parse_args()
    import_capture(args.captures, args.destination, url=args.url, title=args.title,
                   first=args.first, last=args.last)


if __name__ == "__main__":
    main()
