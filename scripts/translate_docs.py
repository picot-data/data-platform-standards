"""Generates French and Dutch translations of the English docs, at build time.

Runs before `mkdocs build` in CI so docs/*.fr.md and docs/*.nl.md are always
regenerated from the current docs/*.md — there is no hand-maintained
translation file to forget to update, and the two languages can never drift
from the English source. The generated files are gitignored, not committed:
build output, same as site/.

Diagrams stay English on every language: they are pulled into each page via
"--8<-- docs/assets/diagrams/*.svg" snippet-include lines, which this script
copies through untouched rather than translating the SVG itself.

Each translation is cached under .translation-cache/<locale>/<hash>.md, keyed
on a hash of the English source, PROMPT_VERSION and the locale. CI restores
that directory from actions/cache before running this script (see
.github/workflows/docs.yml), so a page whose English content hasn't changed
is served from cache instead of spending a Swiftask call on it. Bump
PROMPT_VERSION whenever SYSTEM_PROMPT changes, to invalidate every cached
translation at once rather than leaving stale ones behind under the old rules.

Requires SWIFTASK_API_KEY in the environment. Uses Swiftask's OpenAI-SDK-
compatible endpoint — see https://docs.swiftask.ai/fr/help/articles/8458754.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
MKDOCS_YML = ROOT / "mkdocs.yml"
CACHE_DIR = ROOT / ".translation-cache"

LANGUAGES = {"fr": "French", "nl": "Dutch"}

# Bump this when SYSTEM_PROMPT (or the translation logic) changes, so every
# cached translation is invalidated instead of silently reused under stale
# rules.
PROMPT_VERSION = 1

SYSTEM_PROMPT = """\
You are translating technical documentation for a data platform standards \
site from English to {language}.

Rules:
- Translate prose only. Never translate, and copy through exactly as-is: \
code blocks, inline code, Markdown/HTML syntax, file paths, URLs, section \
anchors (#some-anchor), dbt model names (stg_/int_/dim_/fct_/mart_ \
prefixes), column names, Azure resource names, ADR numbers, and any line \
starting with "--8<--" (a snippet-include directive, not text).
- Keep product and tool names untranslated: dbt, dbt docs, Dagster, \
Metabase, DuckDB, Azure Data Factory, MetricFlow, Parquet, Terraform, \
ADLS.
- Preserve the Markdown structure exactly: headings, tables, lists, code \
fences, links, HTML blocks. Do not add, remove or reorder content.
- Output only the translated Markdown. No preamble, no explanation, no \
surrounding code fence.
"""


def nav_doc_paths() -> list[str]:
    """Every docs/*.md path referenced from mkdocs.yml's nav, in order."""
    with MKDOCS_YML.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    paths: list[str] = []

    def walk(nav_entry) -> None:
        if isinstance(nav_entry, str):
            paths.append(nav_entry)
        elif isinstance(nav_entry, dict):
            for value in nav_entry.values():
                walk(value)
        elif isinstance(nav_entry, list):
            for item in nav_entry:
                walk(item)

    walk(config["nav"])
    return paths


def translated_path(source: Path, locale: str) -> Path:
    return source.with_name(f"{source.stem}.{locale}{source.suffix}")


def cache_path(english: str, locale: str) -> Path:
    digest = hashlib.sha256(
        f"{PROMPT_VERSION}\0{locale}\0{english}".encode("utf-8")
    ).hexdigest()
    return CACHE_DIR / locale / f"{digest}.md"


def translate(client: OpenAI, model: str, text: str, language: str) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(language=language)},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content or ""


def main() -> int:
    api_key = os.environ.get("SWIFTASK_API_KEY")
    if not api_key:
        print("SWIFTASK_API_KEY is not set — skipping translation.", file=sys.stderr)
        return 0

    base_url = os.environ.get("SWIFTASK_BASE_URL", "https://api.swiftask.fr/v1")
    model = os.environ.get("SWIFTASK_MODEL", "claude-haiku-4-5")
    client = OpenAI(api_key=api_key, base_url=base_url)

    for relative_path in nav_doc_paths():
        source = DOCS_DIR / relative_path
        if not source.exists():
            print(f"Skipping {relative_path}: not found", file=sys.stderr)
            continue

        english = source.read_text(encoding="utf-8")
        for locale, language in LANGUAGES.items():
            target = translated_path(source, locale)
            cached = cache_path(english, locale)

            if cached.exists():
                print(f"Cache hit  {relative_path} -> {target.name} ({language})")
                target.write_text(cached.read_text(encoding="utf-8"), encoding="utf-8")
                continue

            print(f"Translating {relative_path} -> {target.name} ({language})")
            try:
                text = translate(client, model, english, language)
            except Exception as exc:  # noqa: BLE001 - a Swiftask hiccup must
                # never break the English site deploy. Falls back to
                # mkdocs-static-i18n's fallback_to_default for this page.
                print(f"  failed: {exc}", file=sys.stderr)
                continue
            target.write_text(text, encoding="utf-8")
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
