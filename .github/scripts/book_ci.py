#!/usr/bin/env python3
"""book_ci.py — CI helpers for a multi-chapter LaTeX book.

Subcommands:
    config          --file ci/pipeline.yaml
    packages        --file ci/pipeline.yaml --book <id>
    verify-packages --file ci/pipeline.yaml --book <id>
    preflight       --master main.tex
    diagnose        --log main.log --log main.blg [--fail-on-warnings]
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path


# ═════════════════════════════════════════════════════════════════════
# shared helpers
# ═════════════════════════════════════════════════════════════════════
COMMENT = re.compile(r"(?<!\\)%.*$")
def strip(line: str) -> str: return COMMENT.sub("", line)
def read(p: Path) -> str: return p.read_text(encoding="utf-8", errors="replace")


def _load_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        print("::error::PyYAML is not installed; add `pip install pyyaml` before this step")
        sys.exit(1)
    if not path.exists():
        print(f"::error file={path}::pipeline config not found")
        sys.exit(1)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _find_book(data: dict, book_id: str) -> dict:
    book = next((b for b in (data.get("books") or []) if b.get("id") == book_id), None)
    if book is None:
        print(f"::error::book '{book_id}' not found in pipeline config")
        sys.exit(1)
    return book


# ═════════════════════════════════════════════════════════════════════
# config
# ═════════════════════════════════════════════════════════════════════
def _engine_flag(engine: str) -> str:
    return {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}[engine]


def _derive(master: str, suffix: str) -> str:
    return str(Path(master).with_suffix(suffix))


def config_cmd(config_path: Path, out_file: str) -> int:
    data = _load_yaml(config_path)
    defaults = data.get("defaults", {}) or {}
    books_in = data.get("books", []) or []
    if not books_in:
        print(f"::error file={config_path}::no books defined")
        return 1

    default_flags = defaults.get("latexmk_flags") or [
        "-file-line-error", "-interaction=nonstopmode", "-synctex=1",
    ]

    books = []
    for b in books_in:
        if "id" not in b or "master" not in b:
            print(f"::error file={config_path}::book entry missing `id` or `master`")
            return 1
        engine = b.get("engine", defaults.get("engine", "pdflatex"))
        bib    = b.get("bib",    defaults.get("bib",    "biber"))
        flags  = b.get("latexmk_flags", default_flags)
        args   = " ".join([_engine_flag(engine), *flags])
        if bib == "none":
            args += " -nobibtex"

        art_in = b.get("artifacts", {}) or {}
        books.append({
            "id":     b["id"],
            "master": b["master"],
            "log":    b.get("log", art_in.get("log", _derive(b["master"], ".log"))),
            "blg":    b.get("blg", art_in.get("blg", _derive(b["master"], ".blg"))),
            "engine": engine,
            "bib":    bib,
            "args":   args,
            "pdf":    art_in.get("pdf", _derive(b["master"], ".pdf")),
            "logs":   art_in.get("logs", "**/*.log\n**/*.blg\n**/*.bbl"),
        })

    release = data.get("release", {}) or {}
    canary  = data.get("canary",  {}) or {}

    def b2s(x): return "true" if x else "false"

    lines = [
        f"matrix={json.dumps(books, separators=(',', ':'))}",
        f"fail_on_warnings={b2s(defaults.get('fail_on_warnings', False))}",
        f"preflight={b2s(defaults.get('preflight', True))}",
        f"fail_fast={b2s(defaults.get('fail_fast', False))}",
        f"timeout_minutes={int(defaults.get('timeout_minutes', 45))}",
        f"artifact_retention_days={int(defaults.get('artifact_retention_days', 90))}",
        f"log_retention_days={int(defaults.get('log_retention_days', 30))}",
        f"work_in_root_file_dir={b2s(defaults.get('work_in_root_file_dir', True))}",
        f"release_enabled={b2s(release.get('enabled', False))}",
        f"release_tag_pattern={release.get('tag_pattern', 'v*')}",
        f"release_attach={','.join(release.get('attach', []))}",
        f"canary_enabled={b2s(canary.get('enabled', False))}",
    ]

    with open(out_file, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"config: loaded {len(books)} book(s) from {config_path}")
    return 0


# ═════════════════════════════════════════════════════════════════════
# packages / verify-packages
# ═════════════════════════════════════════════════════════════════════
PROBES = {
    "fontenc": "fontenc.sty",    "inputenc": "inputenc.sty",
    "lmodern": "lmodern.sty",    "microtype": "microtype.sty",
    "geometry": "geometry.sty",  "fancyhdr": "fancyhdr.sty",
    "titlesec": "titlesec.sty",  "enumitem": "enumitem.sty",
    "caption": "caption.sty",    "subcaption": "subcaption.sty",
    "float": "float.sty",        "booktabs": "booktabs.sty",
    "longtable": "longtable.sty","tabularx": "tabularx.sty",
    "multirow": "multirow.sty",  "makecell": "makecell.sty",
    "colortbl": "colortbl.sty",  "array": "array.sty",
    "amsmath": "amsmath.sty",    "amssymb": "amssymb.sty",
    "pifont": "pifont.sty",      "xcolor": "xcolor.sty",
    "graphicx": "graphicx.sty",  "pgf": "tikz.sty",
    "pgfplots": "pgfplots.sty",  "listings": "listings.sty",
    "tcolorbox": "tcolorbox.sty","biblatex": "biblatex.sty",
    "natbib": "natbib.sty",      "hyperref": "hyperref.sty",
    "cleveref": "cleveref.sty",  "minted": "minted.sty",
    "fontspec": "fontspec.sty",  "polyglossia": "polyglossia.sty",
}

def _merge_pkgs(defaults: dict, extra: dict) -> dict:
    out = {}
    for cat in ("collections", "texlive", "apt", "python", "fonts"):
        out[cat] = list(dict.fromkeys(
            list(defaults.get(cat, []) or []) + list(extra.get(cat, []) or [])
        ))
    return out


def _emit_multiline(out_file: str, key: str, values: list[str]) -> None:
    joined = " ".join(values)
    if out_file == "/dev/stdout":
        print(f"{key}={joined}")
        return
    with open(out_file, "a", encoding="utf-8") as fh:
        fh.write(f"{key}<<__EOF__\n{joined}\n__EOF__\n")


def packages_cmd(config_path: Path, book_id: str, out_file: str) -> int:
    data = _load_yaml(config_path)
    pkgs = data.get("packages", {}) or {}
    method = pkgs.get("install_method", "image")
    book = _find_book(data, book_id)
    merged = _merge_pkgs(pkgs, book.get("extra_packages", {}) or {})

    _emit_multiline(out_file, "install_method", [method])
    _emit_multiline(out_file, "collections",    merged["collections"])
    _emit_multiline(out_file, "texlive",        merged["texlive"])
    _emit_multiline(out_file, "apt",            merged["apt"])
    _emit_multiline(out_file, "python",         merged["python"])
    _emit_multiline(out_file, "fonts",          merged["fonts"])

    print(f"packages[{book_id}]: method={method} "
          f"texlive={len(merged['texlive'])} apt={len(merged['apt'])} "
          f"python={len(merged['python'])} fonts={len(merged['fonts'])}")
    return 0


def verify_packages_cmd(config_path: Path, book_id: str) -> int:
    data = _load_yaml(config_path)
    pkgs = data.get("packages", {}) or {}
    book = _find_book(data, book_id)
    merged = _merge_pkgs(pkgs, book.get("extra_packages", {}) or {})
    missing: list[tuple[str, str]] = []

    if shutil.which("kpsewhich"):
        for name in merged["texlive"]:
            probe = PROBES.get(name, f"{name}.sty")
            r = subprocess.run(["kpsewhich", probe], capture_output=True, text=True)
            if r.returncode != 0 or not r.stdout.strip():
                missing.append(("texlive", name))
                print(f"::error title=Missing TeX package::"
                      f"'{name}' not found (probe: {probe}). "
                      f"Add to ci/pipeline.yaml → packages.texlive.")
    else:
        print("::warning::kpsewhich not on PATH; skipping TeX Live verification")

    APT_BINARY = {"python3-pygments": "pygmentize", "ghostscript": "gs"}
    for tool in merged["apt"]:
        binary = APT_BINARY.get(tool, tool)
        if binary and not shutil.which(binary):
            missing.append(("apt", tool))
            print(f"::error title=Missing apt tool::"
                  f"'{tool}' (binary '{binary}') not on PATH.")

    for mod in merged["python"]:
        r = subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True)
        if r.returncode != 0:
            missing.append(("python", mod))
            print(f"::error title=Missing Python package::'{mod}' not importable.")

    print(f"verify-packages: {len(missing)} missing of "
          f"{sum(len(merged[k]) for k in ('texlive', 'apt', 'python'))} declared")
    return 1 if missing else 0


# ═════════════════════════════════════════════════════════════════════
# preflight
# ═════════════════════════════════════════════════════════════════════
RE_INPUT = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
RE_GRAPH = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}")
RE_BIB   = re.compile(r"\\(?:bibliography|addbibresource)\s*\{([^}]+)\}")
GRAPH_EXT = [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"]


def resolve(base: Path, target: str, exts: list[str]):
    target = target.strip()
    if not target:
        return None
    p = base / target
    if p.suffix and p.exists():
        return p
    for e in exts:
        q = p.with_suffix(e)
        if q.exists():
            return q
    return p if p.exists() else None


def expand(master: Path) -> list[Path]:
    seen, todo = set(), [master.resolve()]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        for line in read(f).splitlines():
            for m in RE_INPUT.finditer(strip(line)):
                hit = resolve(f.parent, m.group(1), [".tex"])
                if hit and hit.resolve() not in seen:
                    todo.append(hit.resolve())
    return sorted(seen)


def preflight(master: Path, root: Path) -> int:
    if not master.exists():
        print(f"::error file={master}::master file not found")
        return 1
    tex = expand(master)
    print(f"preflight: {len(tex)} .tex file(s) reachable from {master}")
    bad, bibs = 0, set()
    for f in tex:
        for line in read(f).splitlines():
            line = strip(line)
            for m in RE_GRAPH.finditer(line):
                if not (resolve(f.parent, m.group(1), GRAPH_EXT)
                        or resolve(root, m.group(1), GRAPH_EXT)):
                    print(f"::error file={f}::missing figure: {m.group(1)}")
                    bad += 1
            for m in RE_BIB.finditer(line):
                for one in m.group(1).split(","):
                    one = one.strip()
                    if resolve(f.parent, one, [".bib"]) or resolve(root, one, [".bib"]):
                        bibs.add(one)
                    else:
                        print(f"::error file={f}::missing bibliography: {one}")
                        bad += 1
    print(f"preflight: {len(bibs)} bibliography file(s) referenced")
    if bad:
        print(f"::error::preflight failed with {bad} problem(s)")
        return 1
    print("preflight: OK")
    return 0


# ═════════════════════════════════════════════════════════════════════
# diagnose
# ═════════════════════════════════════════════════════════════════════
RE_FILELINE = re.compile(
    r"^(?P<file>[^\s:][^:]*?\.(?:tex|sty|cls|def)):(?P<line>\d+):\s*(?P<msg>.+)$"
)
RE_BANG    = re.compile(r"^!\s*(?P<msg>.+?)\s*$")
RE_WARN    = re.compile(
    r"^(?:LaTeX|Package\s+\S+|Class\s+\S+)\s+Warning:\s*(?P<msg>.+?)"
    r"(?:\s+on input line\s+(?P<line>\d+))?\.?$"
)
RE_BIBWARN = re.compile(r"(?:Warning--|WARN\s*-)\s*(?P<msg>.+)$")
RE_BIBERR  = re.compile(r"(?:ERROR\s*-|I couldn't open database file)\s*(?P<msg>.+)$")


def diagnose(logs: list[Path], fail_on_warnings: bool = False) -> int:
    errors, warnings = [], []
    for log in logs:
        if not log.exists():
            print(f"::notice::log not found: {log}")
            continue
        prev_fileline = False
        for raw in read(log).splitlines():
            line = raw.rstrip()
            if not line:
                prev_fileline = False
                continue

            m = RE_FILELINE.match(line)
            if m:
                errors.append((m["file"], m["line"], m["msg"]))
                prev_fileline = True
                continue

            m = RE_BANG.match(line)
            if m:
                if not prev_fileline:
                    errors.append((str(log), None, m["msg"]))
                prev_fileline = False
                continue

            prev_fileline = False

            if log.suffix == ".blg":
                m = RE_BIBERR.search(line)
                if m:
                    errors.append((str(log), None, m["msg"].strip()))
                    continue
                m = RE_BIBWARN.search(line)
                if m:
                    warnings.append((str(log), None, m["msg"].strip()))
                    continue

            m = RE_WARN.match(line)
            if m:
                warnings.append((str(log), m["line"], m["msg"]))

    for f, ln, msg in errors:
        loc = f"file={f}" + (f",line={ln}" if ln else "")
        print(f"::error {loc}::{msg}")
    for f, ln, msg in warnings:
        loc = f"file={f}" + (f",line={ln}" if ln else "")
        print(f"::warning {loc}::{msg}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## LaTeX build report\n\n")
            fh.write(f"- **errors:** {len(errors)}\n- **warnings:** {len(warnings)}\n\n")
            if errors:
                fh.write("### Errors\n\n")
                for f, ln, msg in errors[:50]:
                    fh.write(f"- `{f}`{f':{ln}' if ln else ''} — {msg}\n")
            if warnings:
                fh.write("\n### Warnings\n\n")
                for f, ln, msg in warnings[:50]:
                    fh.write(f"- `{f}`{f':{ln}' if ln else ''} — {msg}\n")

    print(f"diagnose: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        return 1
    if fail_on_warnings and warnings:
        print("::error::fail_on_warnings is true and the build produced warnings")
        return 1
    return 0


# ═════════════════════════════════════════════════════════════════════
# main
# ═════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("config")
    c.add_argument("--file", default="ci/pipeline.yaml")
    c.add_argument("--out",  default=os.environ.get("GITHUB_OUTPUT", "/dev/stdout"))

    pk = sub.add_parser("packages")
    pk.add_argument("--file", default="ci/pipeline.yaml")
    pk.add_argument("--book", required=True)
    pk.add_argument("--out",  default=os.environ.get("GITHUB_OUTPUT", "/dev/stdout"))

    vp = sub.add_parser("verify-packages")
    vp.add_argument("--file", default="ci/pipeline.yaml")
    vp.add_argument("--book", required=True)

    p = sub.add_parser("preflight")
    p.add_argument("--master", default="main.tex")
    p.add_argument("--root",   default=".")

    d = sub.add_parser("diagnose")
    d.add_argument("--log", action="append", default=[])
    d.add_argument("--fail-on-warnings", action="store_true")

    a = ap.parse_args()
    if a.cmd == "config":
        return config_cmd(Path(a.file), a.out)
    if a.cmd == "packages":
        return packages_cmd(Path(a.file), a.book, a.out)
    if a.cmd == "verify-packages":
        return verify_packages_cmd(Path(a.file), a.book)
    if a.cmd == "preflight":
        return preflight(Path(a.master), Path(a.root))
    return diagnose([Path(x) for x in a.log], fail_on_warnings=a.fail_on_warnings)


if __name__ == "__main__":
    sys.exit(main())