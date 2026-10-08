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

Swiftask reports some failures (out of credits, for one) as a normal 200
completion whose content is the error message. Every translation, fresh or
cached, is therefore checked against its English source before it is used: a
rejected one is never written or cached, the page falls back to English via
mkdocs-static-i18n's fallback_to_default, and the failure is surfaced as a
GitHub Actions warning and in the job summary. Cached entries are checked too,
so a bad translation cached by an earlier run is dropped and retried rather
than served forever. After MAX_CONSECUTIVE_FAILURES failures in a row the
script stops calling Swiftask for the rest of the run (still serving cache
hits) instead of burning one doomed call per page.

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

# A translation outside this length range relative to its English source is
# rejected: French and Dutch run about 10-20% longer than English, so a
# result far outside it is an error message or a truncated answer, not a
# translation.
MIN_LENGTH_RATIO = 0.5
MAX_LENGTH_RATIO = 2.0

# Consecutive failures after which Swiftask is assumed down or out of
# credits, and the remaining pages fall back to English without a call.
MAX_CONSECUTIVE_FAILURES = 3

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


class TranslationError(Exception):
    pass


def check_translation(english: str, translation: str) -> None:
    """Raises TranslationError if `translation` can't be a translation of `english`."""
    if not translation.strip():
        raise TranslationError("empty response")
    ratio = len(translation) / max(len(english), 1)
    if not MIN_LENGTH_RATIO <= ratio <= MAX_LENGTH_RATIO:
        raise TranslationError(
            f"response is {ratio:.0%} of the English length, "
            f"starts with: {translation.strip()[:80]!r}"
        )


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
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise TranslationError("response truncated at max_tokens")
    translation = choice.message.content or ""
    check_translation(text, translation)
    return translation


def report_failures(failures: list[str]) -> None:
    """Surfaces untranslated pages as Actions annotations and in the job summary."""
    if not failures:
        return
    for failure in failures:
        print(f"::warning title=Translation fell back to English::{failure}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Pages served in English instead of their translation\n\n")
            f.writelines(f"- {failure}\n" for failure in failures)


def main() -> int:
    api_key = os.environ.get("SWIFTASK_API_KEY")
    if not api_key:
        print("SWIFTASK_API_KEY is not set — skipping translation.", file=sys.stderr)
        return 0

    base_url = os.environ.get("SWIFTASK_BASE_URL", "https://api.swiftask.fr/v1")
    model = os.environ.get("SWIFTASK_MODEL", "claude-haiku-4-5")
    client = OpenAI(api_key=api_key, base_url=base_url)

    failures: list[str] = []
    consecutive_failures = 0

    for relative_path in nav_doc_paths():
        source = DOCS_DIR / relative_path
        if not source.exists():
            print(f"Skipping {relative_path}: not found", file=sys.stderr)
            continue

        english = source.read_text(encoding="utf-8")
        for locale, language in LANGUAGES.items():
            target = translated_path(source, locale)
            cached = cache_path(english, locale)
            # Removed up front so a failed page falls back to English rather
            # than to a stale translation left over from an earlier run.
            target.unlink(missing_ok=True)

            if cached.exists():
                text = cached.read_text(encoding="utf-8")
                try:
                    check_translation(english, text)
                except TranslationError as exc:
                    print(f"Bad cache  {relative_path} ({language}): {exc}", file=sys.stderr)
                    cached.unlink()
                else:
                    print(f"Cache hit  {relative_path} -> {target.name} ({language})")
                    target.write_text(text, encoding="utf-8")
                    continue

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                failures.append(f"{relative_path} ({language}): skipped, Swiftask unavailable")
                continue

            print(f"Translating {relative_path} -> {target.name} ({language})")
            try:
                text = translate(client, model, english, language)
            except Exception as exc:  # noqa: BLE001 - a Swiftask hiccup must
                # never break the English site deploy. Falls back to
                # mkdocs-static-i18n's fallback_to_default for this page.
                print(f"  failed: {exc}", file=sys.stderr)
                failures.append(f"{relative_path} ({language}): {exc}")
                consecutive_failures += 1
                continue
            consecutive_failures = 0
            target.write_text(text, encoding="utf-8")
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(text, encoding="utf-8")

    report_failures(failures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
