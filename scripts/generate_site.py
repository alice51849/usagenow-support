#!/usr/bin/env python3
"""Generate the deterministic exact-50 UsageNow support and privacy website."""

from __future__ import annotations

import argparse
import datetime
import html
import json
import pathlib
import urllib.parse
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "source"
LOCALE_ROOT = SOURCE_ROOT / "locales"
SITE_PATH = SOURCE_ROOT / "site.json"
PAGES = ("index", "support", "privacy")
PAGE_FILES = {
    "index": "index.html",
    "support": "support.html",
    "privacy": "privacy.html",
}
SECTION_IDS = {
    "home": (
        "direct_connections",
        "credential_storage",
        "widget_watch",
        "purchase",
    ),
    "support": (
        "getting_started",
        "sign_in_again",
        "widget_refresh",
        "offline_rate_limit",
        "sort_language",
        "sign_out_delete",
        "purchase_restore",
        "safe_contact",
        "provider_independence",
    ),
    "privacy": (
        "credential_storage",
        "provider_requests",
        "developer_boundary",
        "local_records",
        "app_group_watch",
        "storekit",
        "excluded_practices",
        "deletion",
        "support_site",
        "provider_independence",
        "policy_changes",
    ),
}
RTL = {"ar-SA", "he", "ur-PK"}
OG_LOCALES = {
    "ar-SA": "ar_SA",
    "bn-BD": "bn_BD",
    "ca": "ca_ES",
    "zh-Hans": "zh_CN",
    "zh-Hant": "zh_TW",
    "hr": "hr_HR",
    "cs": "cs_CZ",
    "da": "da_DK",
    "nl-NL": "nl_NL",
    "en-AU": "en_AU",
    "en-CA": "en_CA",
    "en-GB": "en_GB",
    "en-US": "en_US",
    "fi": "fi_FI",
    "fr-CA": "fr_CA",
    "fr-FR": "fr_FR",
    "de-DE": "de_DE",
    "el": "el_GR",
    "gu-IN": "gu_IN",
    "he": "he_IL",
    "hi": "hi_IN",
    "hu": "hu_HU",
    "id": "id_ID",
    "it": "it_IT",
    "ja": "ja_JP",
    "kn-IN": "kn_IN",
    "ko": "ko_KR",
    "ms": "ms_MY",
    "ml-IN": "ml_IN",
    "mr-IN": "mr_IN",
    "no": "nb_NO",
    "or-IN": "or_IN",
    "pl": "pl_PL",
    "pt-BR": "pt_BR",
    "pt-PT": "pt_PT",
    "pa-IN": "pa_IN",
    "ro": "ro_RO",
    "ru": "ru_RU",
    "sk": "sk_SK",
    "sl-SI": "sl_SI",
    "es-MX": "es_MX",
    "es-ES": "es_ES",
    "sv": "sv_SE",
    "ta-IN": "ta_IN",
    "te-IN": "te_IN",
    "th": "th_TH",
    "tr": "tr_TR",
    "uk": "uk_UA",
    "ur-PK": "ur_PK",
    "vi": "vi_VN",
}
SITE_KEYS = {
    "brand",
    "short_brand",
    "email",
    "updated",
    "canonical_base_url",
    "locales",
}
LOCALE_KEYS = {
    "language_name",
    "language_label",
    "navigation_label",
    "skip_link",
    "nav",
    "contact",
    "footer",
    "home",
    "support",
    "privacy",
}
NAV_KEYS = set(PAGES)
CONTACT_KEYS = {"title", "body", "button"}
PAGE_KEYS = {
    "home": {"title", "summary", "section_title", "sections"},
    "support": {"title", "summary", "section_title", "sections"},
    "privacy": {"title", "summary", "updated_label", "section_title", "sections"},
}
SECTION_KEYS = {"id", "title", "body"}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def require_text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{context}: expected non-empty text")
    return value


def load_site() -> dict[str, Any]:
    try:
        site = json.loads(SITE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"cannot read source/site.json: {error}") from error
    if set(site) != SITE_KEYS:
        raise SystemExit("source/site.json keys are not exact")
    for key in SITE_KEYS - {"locales"}:
        require_text(site[key], f"site.{key}")
    locales = site["locales"]
    if not isinstance(locales, list) or len(locales) != 50:
        raise SystemExit("site.locales must contain exactly 50 entries")
    if any(not isinstance(locale, str) or not locale for locale in locales):
        raise SystemExit("site.locales contains an invalid identifier")
    if len(set(locales)) != len(locales):
        raise SystemExit("site.locales contains duplicates")
    if set(locales) != set(OG_LOCALES):
        raise SystemExit("site.locales does not match the official exact-50 set")
    base = urllib.parse.urlparse(site["canonical_base_url"])
    if (
        base.scheme != "https"
        or not base.netloc
        or base.username
        or base.password
        or base.query
        or base.fragment
        or not site["canonical_base_url"].endswith("/")
    ):
        raise SystemExit("canonical_base_url must be an absolute trailing-slash HTTPS URL")
    if site["email"] != "hourstag.app@gmail.com":
        raise SystemExit("public contact email is not the authorized address")
    if site["brand"] != "UsageNow: AI Usage Tracker" or site["short_brand"] != "UsageNow":
        raise SystemExit("site brand does not match the UsageNow product contract")
    try:
        datetime.date.fromisoformat(site["updated"])
    except ValueError as error:
        raise SystemExit("site.updated must be an ISO calendar date") from error
    return site


SITE = load_site()
LOCALES = tuple(SITE["locales"])
BASE_URL = SITE["canonical_base_url"]
EMAIL = SITE["email"]
UPDATED = SITE["updated"]
BRAND = SITE["brand"]
SHORT_BRAND = SITE["short_brand"]


def validate_sections(locale: str, page: str, value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise SystemExit(f"{locale}.{page}.sections: expected a list")
    expected_ids = SECTION_IDS[page]
    if len(value) != len(expected_ids):
        raise SystemExit(f"{locale}.{page}.sections: wrong section count")
    sections: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict) or set(raw) != SECTION_KEYS:
            raise SystemExit(f"{locale}.{page}.sections[{index}]: schema is not exact")
        section = {key: require_text(raw[key], f"{locale}.{page}.{index}.{key}") for key in SECTION_KEYS}
        sections.append(section)
    actual_ids = tuple(section["id"] for section in sections)
    if actual_ids != expected_ids:
        raise SystemExit(f"{locale}.{page}.sections: identifiers are not exact or ordered")
    return sections


def load_translations() -> dict[str, dict[str, Any]]:
    files = {path.stem: path for path in LOCALE_ROOT.glob("*.json")}
    if set(files) != set(LOCALES):
        missing = ", ".join(sorted(set(LOCALES) - set(files))) or "none"
        extra = ", ".join(sorted(set(files) - set(LOCALES))) or "none"
        raise SystemExit(f"locale files mismatch; missing: {missing}; extra: {extra}")
    translations: dict[str, dict[str, Any]] = {}
    for locale in LOCALES:
        try:
            item = json.loads(files[locale].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"{locale}: cannot read locale source: {error}") from error
        if not isinstance(item, dict) or set(item) != LOCALE_KEYS:
            raise SystemExit(f"{locale}: locale keys are not exact")
        for key in ("language_name", "language_label", "navigation_label", "skip_link", "footer"):
            require_text(item[key], f"{locale}.{key}")
        if not isinstance(item["nav"], dict) or set(item["nav"]) != NAV_KEYS:
            raise SystemExit(f"{locale}.nav: keys are not exact")
        for key in PAGES:
            require_text(item["nav"][key], f"{locale}.nav.{key}")
        if not isinstance(item["contact"], dict) or set(item["contact"]) != CONTACT_KEYS:
            raise SystemExit(f"{locale}.contact: keys are not exact")
        for key in CONTACT_KEYS:
            require_text(item["contact"][key], f"{locale}.contact.{key}")
        for page in ("home", "support", "privacy"):
            block = item[page]
            if not isinstance(block, dict) or set(block) != PAGE_KEYS[page]:
                raise SystemExit(f"{locale}.{page}: keys are not exact")
            for key in PAGE_KEYS[page] - {"sections"}:
                require_text(block[key], f"{locale}.{page}.{key}")
            block["sections"] = validate_sections(locale, page, block["sections"])
        translations[locale] = item
    return translations


def page_url(locale: str | None, page: str) -> str:
    prefix = f"{locale}/" if locale else ""
    suffix = "" if page == "index" else PAGE_FILES[page]
    return f"{BASE_URL}{prefix}{suffix}"


def output_path(locale: str | None, page: str) -> pathlib.Path:
    if locale is None:
        return ROOT / PAGE_FILES[page]
    return ROOT / locale / PAGE_FILES[page]


def relative_page_href(current_locale: str | None, target_locale: str | None, page: str) -> str:
    suffix = "" if page == "index" else PAGE_FILES[page]
    if current_locale == target_locale:
        return "./" if page == "index" else suffix
    if current_locale is None:
        return f"{target_locale}/{suffix}" if target_locale else ("./" if page == "index" else suffix)
    if target_locale is None:
        return f"../{suffix}" if suffix else "../"
    return f"../{target_locale}/{suffix}"


def asset_href(locale: str | None, filename: str) -> str:
    return f"{'../' if locale else ''}assets/{filename}"


def alternate_markup(page: str) -> str:
    rows = [
        f'<link rel="alternate" hreflang="{locale}" href="{esc(page_url(locale, page))}">'
        for locale in LOCALES
    ]
    rows.append(
        f'<link rel="alternate" hreflang="x-default" href="{esc(page_url(None, page))}">'
    )
    return "\n  ".join(rows)


def navigation_markup(locale: str | None, page: str, labels: dict[str, str]) -> str:
    rows = []
    for candidate in PAGES:
        active = ' aria-current="page"' if candidate == page else ""
        rows.append(
            f'<a href="{esc(relative_page_href(locale, locale, candidate))}"{active}>'
            f'{esc(labels[candidate])}</a>'
        )
    return "\n        ".join(rows)


def language_picker_markup(
    translations: dict[str, dict[str, Any]], locale: str | None, page: str
) -> str:
    rows = []
    for candidate in LOCALES:
        active = ' aria-current="page"' if candidate == locale else ""
        rows.append(
            f'<li><a lang="{candidate}" hreflang="{candidate}" dir="auto" '
            f'href="{esc(relative_page_href(locale, candidate, page))}"{active}>'
            f'{esc(translations[candidate]["language_name"])}</a></li>'
        )
    return "\n          ".join(rows)


def section_markup(page: str, item: dict[str, Any]) -> str:
    cards = "\n".join(
        (
            f'<li><article class="card" data-fact="{esc(section["id"])}">'
            f'<h3>{esc(section["title"])}</h3><p>{esc(section["body"])}</p>'
            "</article></li>"
        )
        for section in item[page]["sections"]
    )
    policy_class = " policy-grid" if page == "privacy" else ""
    return (
        f'<section aria-labelledby="{page}-sections-heading">\n'
        f'  <h2 class="section-heading" id="{page}-sections-heading">'
        f'{esc(item[page]["section_title"])}</h2>\n'
        f'  <ul class="section-grid{policy_class}" role="list">\n'
        f"    {cards}\n"
        "  </ul>\n"
        "</section>"
    )


def contact_markup(item: dict[str, Any]) -> str:
    contact = item["contact"]
    return (
        '<section class="card contact-card" aria-labelledby="contact-heading">\n'
        f'  <h2 id="contact-heading">{esc(contact["title"])}</h2>\n'
        f'  <p>{esc(contact["body"])}</p>\n'
        '  <address class="contact-actions">\n'
        # The canonical host runs Cloudflare Email Obfuscation, which rewrites
        # bare addresses and mailto links; email_off markers keep them intact.
        f'    <!--email_off--><a class="mail-button" href="mailto:{EMAIL}" '
        f'aria-label="{esc(contact["button"])} {EMAIL}"><span>{EMAIL}</span></a>'
        "<!--/email_off-->\n"
        "  </address>\n"
        "</section>"
    )


def render_page(
    translations: dict[str, dict[str, Any]], locale: str | None, page: str
) -> str:
    content_locale = locale or "en-US"
    item = translations[content_locale]
    source_page = "home" if page == "index" else page
    block = item[source_page]
    direction = "rtl" if content_locale in RTL else "ltr"
    canonical = page_url(locale, page)
    title = f'{block["title"]} — {BRAND}'
    is_router = locale is None and page == "index"
    script_policy = "'self'" if is_router else "'none'"
    router = (
        f'\n  <script src="{asset_href(locale, "locale-redirect.js")}" defer></script>'
        if is_router
        else ""
    )
    updated = (
        f'\n        <p class="updated">{esc(block["updated_label"])}: '
        f'<time datetime="{UPDATED}" dir="ltr">{UPDATED}</time></p>'
        if page == "privacy"
        else ""
    )
    return f"""<!doctype html>
<!-- Generated by scripts/generate_site.py. Do not edit directly. -->
<html lang="{content_locale}" dir="{direction}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="light dark">
  <meta name="theme-color" content="#fffaff" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#17092d" media="(prefers-color-scheme: dark)">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="referrer" content="no-referrer">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src {script_policy}; connect-src 'none'; font-src 'none'; object-src 'none'; frame-src 'none'; media-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(block["summary"])}">
  <link rel="canonical" href="{esc(canonical)}">
  {alternate_markup(page)}
  <link rel="icon" href="{asset_href(locale, "site-mark.svg")}" type="image/svg+xml">
  <link rel="stylesheet" href="{asset_href(locale, "site.css")}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{esc(BRAND)}">
  <meta property="og:locale" content="{OG_LOCALES[content_locale]}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(block["summary"])}">
  <meta property="og:url" content="{esc(canonical)}">{router}
</head>
<body>
  <a class="skip-link" href="#main">{esc(item["skip_link"])}</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{esc(relative_page_href(locale, locale, "index"))}" dir="ltr">
        <img src="{asset_href(locale, "site-mark.svg")}" width="64" height="64" alt="">
        <span>{esc(BRAND)}</span>
      </a>
      <nav class="primary-nav" aria-label="{esc(item["navigation_label"])}">
        {navigation_markup(locale, page, item["nav"])}
      </nav>
      <details class="language-picker">
        <summary>{esc(item["language_label"])}</summary>
        <ul class="language-list" role="list">
          {language_picker_markup(translations, locale, page)}
        </ul>
      </details>
    </div>
  </header>
  <main class="page-shell" id="main" tabindex="-1">
    <header class="hero">
      <div>
        <p class="eyebrow">{esc(SHORT_BRAND)}</p>
        <h1>{esc(block["title"])}</h1>
        <p class="lead">{esc(block["summary"])}</p>{updated}
      </div>
      <div class="hero-art" aria-hidden="true">
        <img class="hero-mark" src="{asset_href(locale, "site-mark.svg")}" width="256" height="256" alt="">
      </div>
    </header>
    {section_markup(source_page, item)}
    {contact_markup(item)}
  </main>
  <footer class="site-footer">
    <div class="footer-inner">
      <p>{esc(item["footer"])}</p>
    </div>
  </footer>
</body>
</html>
"""


def render_sitemap() -> str:
    urls = [page_url(None, page) for page in PAGES]
    urls.extend(page_url(locale, page) for locale in LOCALES for page in PAGES)
    rows = "\n".join(
        f"  <url><loc>{esc(url)}</loc><lastmod>{UPDATED}</lastmod></url>" for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def expected_outputs(translations: dict[str, dict[str, Any]]) -> dict[pathlib.Path, str]:
    outputs = {
        output_path(locale, page): render_page(translations, locale, page)
        for locale in (None, *LOCALES)
        for page in PAGES
    }
    outputs[ROOT / "sitemap.xml"] = render_sitemap()
    outputs[ROOT / "robots.txt"] = (
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n"
    )
    return outputs


def write_outputs(outputs: dict[pathlib.Path, str]) -> None:
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Generated {3 * (len(LOCALES) + 1)} HTML pages for {len(LOCALES)} locales.")


def check_outputs(outputs: dict[pathlib.Path, str]) -> None:
    failures = []
    for path, expected in outputs.items():
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
        elif path.read_text(encoding="utf-8") != expected:
            failures.append(f"stale {path.relative_to(ROOT)}")
    expected_html = {path.resolve() for path in outputs if path.suffix == ".html"}
    actual_html = {path.resolve() for path in ROOT.rglob("*.html")}
    failures.extend(
        f"unexpected {path.relative_to(ROOT.resolve())}"
        for path in sorted(actual_html - expected_html)
    )
    if failures:
        raise SystemExit("\n".join(f"FAIL: {failure}" for failure in failures))
    print(f"PASS generator check: {len(expected_html)} deterministic HTML pages.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = expected_outputs(load_translations())
    check_outputs(outputs) if args.check else write_outputs(outputs)


if __name__ == "__main__":
    main()
