#!/usr/bin/env python3
"""Fail-closed validation for the UsageNow exact-50 static website."""

from __future__ import annotations

import collections
import difflib
import pathlib
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from generate_site import (  # noqa: E402
    BASE_URL,
    BRAND,
    EMAIL,
    LOCALES,
    OG_LOCALES,
    PAGE_FILES,
    PAGES,
    ROOT,
    RTL,
    SECTION_IDS,
    SITE,
    expected_outputs,
    load_translations,
    page_url,
    render_sitemap,
    relative_page_href,
)

EXPECTED_PAGES = 3 * (len(LOCALES) + 1)
FORBIDDEN_PUBLIC_EMAIL = "alice51849" + "@" + "hotmail.com"
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME)\b|(?i:lorem ipsum)|\?\?\?|\{\{|ZXQ(?:TERM|SEG)"
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
# The canonical Cloudflare host obfuscates addresses outside these markers.
EMAIL_SHIELD_RE = re.compile(r"<!--email_off-->.*?<!--/email_off-->", re.S)
PRICE_RE = re.compile(
    r"(?:US\$|AU\$|CA\$|NZ\$|HK\$|NT\$|[$€£¥₹₩₽])\s*\d|"
    r"\d[\d.,]*\s*(?:USD|EUR|GBP|AUD|CAD)"
)
TRACKING_CODE_RE = re.compile(
    r"google-analytics|googletagmanager|gtag\s*\(|facebook(?:\.net| pixel)|"
    r"mixpanel|segment\.com|hotjar|doubleclick|fingerprintjs|"
    r"document\.cookie|localStorage|sessionStorage|fetch\s*\(|XMLHttpRequest",
    re.I,
)
FORBIDDEN_CLAIM_RE = re.compile(
    r"\b(?:completely offline|never connects|no network access|"
    r"does not collect personal data|data not collected)\b",
    re.I,
)
PROVIDER_NAMES = {
    "Claude",
    "Anthropic",
    "ChatGPT",
    "Codex",
    "OpenAI",
    "GitHub Copilot",
    "GitHub",
    "Microsoft",
    "Gemini",
    "Google",
}
VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
SCRIPT_RANGES = {
    "ar-SA": r"[\u0600-\u06ff]",
    "bn-BD": r"[\u0980-\u09ff]",
    "zh-Hans": r"[\u3400-\u9fff]",
    "zh-Hant": r"[\u3400-\u9fff]",
    "el": r"[\u0370-\u03ff]",
    "gu-IN": r"[\u0a80-\u0aff]",
    "he": r"[\u0590-\u05ff]",
    "hi": r"[\u0900-\u097f]",
    "ja": r"[\u3040-\u30ff]",
    "kn-IN": r"[\u0c80-\u0cff]",
    "ko": r"[\uac00-\ud7af]",
    "ml-IN": r"[\u0d00-\u0d7f]",
    "mr-IN": r"[\u0900-\u097f]",
    "or-IN": r"[\u0b00-\u0b7f]",
    "pa-IN": r"[\u0a00-\u0a7f]",
    "ru": r"[\u0400-\u04ff]",
    "ta-IN": r"[\u0b80-\u0bff]",
    "te-IN": r"[\u0c00-\u0c7f]",
    "th": r"[\u0e00-\u0e7f]",
    "uk": r"[\u0400-\u04ff]",
    "ur-PK": r"[\u0600-\u06ff]",
}
NEGATED_FACTS = (
    ("support", "sign_in_again"),
    ("support", "safe_contact"),
    ("support", "provider_independence"),
    ("privacy", "credential_storage"),
    ("privacy", "developer_boundary"),
    ("privacy", "app_group_watch"),
    ("privacy", "excluded_practices"),
    ("privacy", "provider_independence"),
)
NEGATION_MARKERS = {
    "ar": ("لا", "ليس", "بدون"),
    "bn": ("না", "নয়", "ছাড়া"),
    "ca": (" no ", "sense ", "mai "),
    "zh": ("不", "無", "没有", "不会", "不得", "絕不", "绝不", "切勿"),
    "hr": (" ne", "bez ", "nikad"),
    "cs": (" ne", "bez ", "nikdy"),
    "da": ("ikke", "aldrig", "uden"),
    "nl": ("niet", "geen", "zonder", "nooit"),
    "en": (" not ", " no ", "never", "without", "cannot", "does not", "do not"),
    "fi": (" ei ", "älä", "ilman", "eivät"),
    "fr": (" ne ", " pas", "jamais", "sans ", "aucun"),
    "de": ("nicht", "kein", "ohne", "niemals"),
    "el": ("δεν", "χωρίς", "ποτέ", "μην"),
    "gu": ("નહીં", "નથી", "ના ", "વિના"),
    "he": ("לא", "אינו", "אינם", "בלי", "אל "),
    "hi": ("नहीं", "बिना", "मत ", "न करें"),
    "hu": (" nem ", "nincs", "soha", "nélkül"),
    "id": ("tidak", "jangan", "tanpa", "bukan"),
    "it": (" non ", "senza", "mai"),
    "ja": ("ない", "ません", "せず", "禁止"),
    "kn": ("ಲ್ಲ", "ಬೇಡ", "ರಹಿತ"),
    "ko": ("않", "없", "마세요", "금지"),
    "ms": ("tidak", "jangan", "tanpa", "bukan"),
    "ml": ("ല്ല", "രുത്", "രഹിത"),
    "mr": ("नाही", "नका", "शिवाय"),
    "no": ("ikke", "aldri", "uten"),
    "or": ("ନାହିଁ", "ନୁହେଁ", "ବିନା"),
    "pl": (" nie ", "bez", "nigdy"),
    "pt": (" não ", "sem ", "nunca"),
    "pa": ("ਨਹੀਂ", "ਨਾ ", "ਬਿਨਾਂ"),
    "ro": (" nu ", "fără", "niciodată"),
    "ru": (" не ", "нет", "никогда", "без"),
    "sk": (" ne", "bez", "nikdy"),
    "sl": (" ne ", "brez", "nikoli"),
    "es": (" no ", "sin ", "nunca"),
    "sv": ("inte", "utan", "aldrig"),
    "ta": ("இல்லை", "வேண்டாம்", "இன்றி", "அல்ல"),
    "te": (
        "లేదు",
        "లేవు",
        "వద్దు",
        "కాదు",
        "లేకుండా",
        "చేయదు",
        "చేయవు",
        "ఉండవు",
        "కావు",
        "అందవు",
        "వెళ్లవు",
        "అడగదు",
        "పిలవదు",
        "దాటదు",
    ),
    "th": ("ไม่", "ห้าม", "โดยไม่มี"),
    "tr": ("değil", "olmadan", "göndermeyin", "yok", "maz", "mez"),
    "uk": (" не ", "немає", "ніколи", "без"),
    "ur": ("نہیں", "نہ ", "بغیر", "مت "),
    "vi": (" không", "đừng", "chưa", "chẳng"),
}
REQUIRED_TOKENS = {
    ("home", "direct_connections"): {"API", "HTTPS"},
    ("home", "credential_storage"): {"Keychain", "AfterFirstUnlockThisDeviceOnly", "Widget", "iCloud", "Apple Watch"},
    ("home", "widget_watch"): {"Widget", "Apple Watch"},
    ("home", "purchase"): {"StoreKit", "UsageNow Pro"},
    ("support", "getting_started"): {"GitHub"},
    ("support", "widget_refresh"): {"Widget"},
    ("support", "offline_rate_limit"): {"429"},
    ("support", "sort_language"): {"50", "Widget", "Apple Watch"},
    ("support", "sign_out_delete"): {"Keychain", "Widget", "Apple Watch"},
    ("support", "purchase_restore"): {"StoreKit", "UsageNow Pro", "Apple Account"},
    ("support", "safe_contact"): {"URL"},
    ("privacy", "credential_storage"): {"Keychain", "AfterFirstUnlockThisDeviceOnly", "Widget", "iCloud", "Apple Watch"},
    ("privacy", "provider_requests"): {"API", "HTTPS", "VPN"},
    ("privacy", "app_group_watch"): {"App Group", "Widget", "WatchConnectivity", "Apple Watch"},
    ("privacy", "storekit"): {"StoreKit", "UsageNow Pro"},
    ("privacy", "deletion"): {"Keychain", "Widget", "Apple Watch"},
    ("privacy", "support_site"): {"GitHub Pages"},
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.html: dict[str, str] = {}
        self.canonical: list[str] = []
        self.alternates: dict[str, list[str]] = collections.defaultdict(list)
        self.metas: dict[str, list[str]] = collections.defaultdict(list)
        self.anchors: list[str] = []
        self.mail_links: list[dict[str, str]] = []
        self.resources: list[str] = []
        self.language_links: dict[str, list[str]] = collections.defaultdict(list)
        self.scripts: list[dict[str, str]] = []
        self.ids: set[str] = set()
        self.facts: list[str] = []
        self.main_attrs: list[dict[str, str]] = []
        self.nav_count = 0
        self.h1_count = 0
        self.doctype = False

    def handle_decl(self, declaration: str) -> None:
        self.doctype = declaration.lower() == "doctype html"

    def handle_starttag(
        self, tag: str, attrs_list: list[tuple[str, str | None]]
    ) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        if tag not in VOID:
            self.stack.append(tag)
        if "style" in attrs:
            self.errors.append(f"inline style on <{tag}>")
        if any(key.lower().startswith("on") for key in attrs):
            self.errors.append(f"inline event handler on <{tag}>")
        if tag in {"iframe", "form", "object", "embed"}:
            self.errors.append(f"forbidden <{tag}>")
        if tag == "html":
            self.html = attrs
        if tag == "main":
            self.main_attrs.append(attrs)
        if tag == "nav":
            self.nav_count += 1
            if not attrs.get("aria-label"):
                self.errors.append("navigation has no aria-label")
        if tag == "h1":
            self.h1_count += 1
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.errors.append(f"duplicate id {attrs['id']}")
            self.ids.add(attrs["id"])
        if "data-fact" in attrs:
            self.facts.append(attrs["data-fact"])
        if tag == "a":
            self.anchors.append(attrs.get("href", ""))
            if "mail-button" in attrs.get("class", "").split():
                self.mail_links.append(attrs)
            if "hreflang" in attrs:
                self.language_links[attrs["hreflang"]].append(attrs.get("href", ""))
        if tag == "link":
            rel = set(attrs.get("rel", "").split())
            if "canonical" in rel:
                self.canonical.append(attrs.get("href", ""))
            if "alternate" in rel and "hreflang" in attrs:
                self.alternates[attrs["hreflang"]].append(attrs.get("href", ""))
            if "stylesheet" in rel or "icon" in rel:
                self.resources.append(attrs.get("href", ""))
        if tag == "img":
            self.resources.append(attrs.get("src", ""))
        if tag == "script":
            self.scripts.append(attrs)
            self.resources.append(attrs.get("src", ""))
        if tag == "meta":
            key = (
                attrs.get("name")
                or attrs.get("property")
                or attrs.get("http-equiv")
            )
            if key:
                self.metas[key].append(attrs.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced closing </{tag}>")
            return
        self.stack.pop()


def all_strings(value: object, path: tuple[object, ...] = ()) -> list[str]:
    if isinstance(value, str):
        return [] if path and path[-1] == "id" else [value]
    if isinstance(value, list):
        result: list[str] = []
        for index, child in enumerate(value):
            result.extend(all_strings(child, (*path, index)))
        return result
    if isinstance(value, dict):
        result = []
        for key, child in value.items():
            result.extend(all_strings(child, (*path, key)))
        return result
    return []


def section_map(item: dict[str, Any], page: str) -> dict[str, dict[str, str]]:
    return {section["id"]: section for section in item[page]["sections"]}


def normalized_locale_text(item: dict[str, Any]) -> str:
    ignored = {item["language_name"]}
    values = [
        text
        for text in all_strings(item)
        if text not in ignored and text not in PROVIDER_NAMES
    ]
    text = " ".join(values).casefold()
    for token in (
        BRAND,
        "UsageNow",
        "AfterFirstUnlockThisDeviceOnly",
        "WatchConnectivity",
        "UsageNow Pro",
        "GitHub Pages",
        "GitHub Copilot",
        "Apple Account",
        "Apple Watch",
        "App Group",
        "Anthropic",
        "Microsoft",
        "ChatGPT",
        "Claude",
        "Codex",
        "GitHub",
        "iCloud",
        "OpenAI",
        "CloudKit",
        "StoreKit",
        "Keychain",
        "Gemini",
        "Google",
        "Widget",
        "Apple",
        "OAuth",
        "HTTPS",
        "HTML",
        "VPN",
        "SSO",
        "API",
        "URL",
    ):
        text = text.replace(token.casefold(), " ")
    return re.sub(r"\s+", " ", text).strip()


def check_sources(
    errors: list[str], translations: dict[str, dict[str, Any]]
) -> None:
    if len(translations) != 50 or set(translations) != set(LOCALES):
        errors.append("translation source is not the official exact-50 set")
        return
    english = translations["en-US"]
    english_text = normalized_locale_text(english)
    for locale in LOCALES:
        item = translations[locale]
        strings = all_strings(item)
        joined = "\n".join(strings)
        if any(not text.strip() for text in strings):
            errors.append(f"{locale}: empty localized string")
        if PLACEHOLDER_RE.search(joined):
            errors.append(f"{locale}: placeholder or bootstrap token remains")
        if PRICE_RE.search(joined):
            errors.append(f"{locale}: hard-coded price")
        if FORBIDDEN_CLAIM_RE.search(joined):
            errors.append(f"{locale}: forbidden blanket privacy or offline claim")
        emails = set(EMAIL_RE.findall(joined))
        if emails:
            errors.append(f"{locale}: email belongs only in source/site.json")
        for page, expected_ids in SECTION_IDS.items():
            actual = tuple(section_map(item, page))
            if actual != expected_ids:
                errors.append(f"{locale}.{page}: required fact sections are not exact")
        for (page, fact), tokens in REQUIRED_TOKENS.items():
            section = section_map(item, page)[fact]
            fact_text = f'{section["title"]}\n{section["body"]}'
            for token in tokens:
                if token not in fact_text:
                    errors.append(f"{locale}.{page}.{fact}: missing technical token {token}")
        negation_markers = NEGATION_MARKERS[locale.split("-")[0]]
        for page, fact in NEGATED_FACTS:
            section = section_map(item, page)[fact]
            fact_text = f' {section["title"]} {section["body"]} '.casefold()
            if not any(
                marker.casefold() in fact_text for marker in negation_markers
            ):
                errors.append(
                    f"{locale}.{page}.{fact}: missing localized negative safety statement"
                )
        for page in ("support", "privacy"):
            independence = section_map(item, page)["provider_independence"]["body"]
            for provider in PROVIDER_NAMES:
                if provider not in independence:
                    errors.append(
                        f"{locale}.{page}.provider_independence: missing {provider}"
                    )
        if locale not in {"en-AU", "en-CA", "en-GB", "en-US"}:
            localized = normalized_locale_text(item)
            ratio = difflib.SequenceMatcher(None, english_text, localized).ratio()
            if ratio >= 0.72:
                errors.append(f"{locale}: possible English fallback similarity {ratio:.3f}")
            for page in ("home", "support", "privacy"):
                if item[page]["summary"] == english[page]["summary"]:
                    errors.append(f"{locale}.{page}: untranslated summary")
        if locale in SCRIPT_RANGES and not re.search(SCRIPT_RANGES[locale], joined):
            errors.append(f"{locale}: expected native script is missing")
    for locale in ("en-AU", "en-CA", "en-GB"):
        if normalized_locale_text(translations[locale]) == english_text:
            errors.append(f"{locale}: regional English copy is identical to en-US")
    for left, right in (
        ("fr-CA", "fr-FR"),
        ("es-MX", "es-ES"),
        ("pt-BR", "pt-PT"),
        ("zh-Hans", "zh-Hant"),
    ):
        if normalized_locale_text(translations[left]) == normalized_locale_text(
            translations[right]
        ):
            errors.append(f"{left} and {right}: regional copy is identical")


def parse_pages(
    paths: set[pathlib.Path], errors: list[str]
) -> dict[pathlib.Path, PageParser]:
    parsed: dict[pathlib.Path, PageParser] = {}
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        parser.close()
        parsed[path.resolve()] = parser
    return parsed


def resolve_relative(
    page_path: pathlib.Path, value: str, errors: list[str], label: str
) -> tuple[pathlib.Path | None, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("/"):
        errors.append(f"{page_path.relative_to(ROOT)}: {label} is not relative: {value}")
        return None, ""
    raw_path = urllib.parse.unquote(parsed.path)
    if not raw_path:
        target = page_path.resolve()
    else:
        target = (page_path.parent / raw_path).resolve()
        if raw_path.endswith("/") or target.is_dir():
            target = target / "index.html"
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"{page_path.relative_to(ROOT)}: {label} escapes site root: {value}")
        return None, ""
    if not target.is_file():
        errors.append(f"{page_path.relative_to(ROOT)}: broken {label}: {value}")
        return None, ""
    return target, parsed.fragment


def check_page(
    path: pathlib.Path,
    locale: str | None,
    page: str,
    parser: PageParser,
    parsed_pages: dict[pathlib.Path, PageParser],
    errors: list[str],
) -> None:
    relative = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    content_locale = locale or "en-US"
    expected_canonical = page_url(locale, page)
    if not parser.doctype:
        errors.append(f"{relative}: missing HTML5 doctype")
    if parser.stack:
        errors.append(f"{relative}: unclosed tags")
    errors.extend(f"{relative}: {error}" for error in parser.errors)
    if parser.html.get("lang") != content_locale:
        errors.append(f"{relative}: wrong html lang")
    if parser.html.get("dir") != ("rtl" if content_locale in RTL else "ltr"):
        errors.append(f"{relative}: wrong direction")
    if parser.main_attrs != [{"class": "page-shell", "id": "main", "tabindex": "-1"}]:
        errors.append(f"{relative}: main landmark or keyboard target is not exact")
    if parser.nav_count != 1 or parser.h1_count != 1:
        errors.append(f"{relative}: expected one primary nav and one h1")
    if parser.canonical != [expected_canonical]:
        errors.append(f"{relative}: canonical is not self-exact")
    expected_hreflangs = set(LOCALES) | {"x-default"}
    if set(parser.alternates) != expected_hreflangs:
        errors.append(f"{relative}: hreflang set is not exact")
    for code in LOCALES:
        if parser.alternates.get(code) != [page_url(code, page)]:
            errors.append(f"{relative}: bad hreflang URL for {code}")
    if parser.alternates.get("x-default") != [page_url(None, page)]:
        errors.append(f"{relative}: bad x-default URL")
    if set(parser.language_links) != set(LOCALES):
        errors.append(f"{relative}: language selector is not exact 50")
    for code in LOCALES:
        expected = relative_page_href(locale, code, page)
        if parser.language_links.get(code) != [expected]:
            errors.append(f"{relative}: bad relative language link for {code}")
    if parser.metas.get("og:url") != [expected_canonical]:
        errors.append(f"{relative}: OpenGraph URL differs from canonical")
    if parser.metas.get("og:locale") != [OG_LOCALES[content_locale]]:
        errors.append(f"{relative}: wrong OpenGraph locale")
    if parser.metas.get("robots") != ["index,follow,max-image-preview:large"]:
        errors.append(f"{relative}: wrong robots metadata")
    if len(parser.metas.get("description", [])) != 1:
        errors.append(f"{relative}: missing unique description")
    expected_facts = SECTION_IDS["home" if page == "index" else page]
    if tuple(parser.facts) != expected_facts:
        errors.append(f"{relative}: rendered data-flow facts are not exact")
    expected_script = locale is None and page == "index"
    if expected_script:
        if parser.scripts != [{"src": "assets/locale-redirect.js", "defer": ""}]:
            errors.append(f"{relative}: root locale router is not exact")
    elif parser.scripts:
        errors.append(f"{relative}: unexpected script")
    expected_script_policy = "'self'" if expected_script else "'none'"
    csp = parser.metas.get("Content-Security-Policy", [])
    if (
        len(csp) != 1
        or f"script-src {expected_script_policy}" not in csp[0]
        or "connect-src 'none'" not in csp[0]
    ):
        errors.append(f"{relative}: Content Security Policy is wrong")
    found_emails = set(EMAIL_RE.findall(text))
    if found_emails != {EMAIL}:
        errors.append(f"{relative}: public email set is not exact")
    if (
        len(parser.mail_links) != 1
        or parser.mail_links[0].get("href") != f"mailto:{EMAIL}"
        or EMAIL not in parser.mail_links[0].get("aria-label", "")
    ):
        errors.append(f"{relative}: accessible support email action is not exact")
    if text.count("<!--email_off-->") != text.count("<!--/email_off-->") or EMAIL_RE.search(
        EMAIL_SHIELD_RE.sub("", text)
    ):
        errors.append(f"{relative}: public email is not shielded by email_off markers")
    if FORBIDDEN_PUBLIC_EMAIL in text:
        errors.append(f"{relative}: forbidden public email")
    if PLACEHOLDER_RE.search(text):
        errors.append(f"{relative}: placeholder or bootstrap token remains")
    if PRICE_RE.search(text):
        errors.append(f"{relative}: hard-coded price")
    if FORBIDDEN_CLAIM_RE.search(text):
        errors.append(f"{relative}: forbidden blanket privacy or offline claim")
    if TRACKING_CODE_RE.search(text):
        errors.append(f"{relative}: tracking or unexpected network code")
    for href in parser.anchors:
        if href.startswith("mailto:"):
            if href != f"mailto:{EMAIL}":
                errors.append(f"{relative}: unauthorized mail link")
            continue
        target, fragment = resolve_relative(path, href, errors, "link")
        if target is not None and fragment:
            target_parser = parsed_pages.get(target.resolve())
            if target_parser is None or fragment not in target_parser.ids:
                errors.append(f"{relative}: missing fragment target {href}")
    for resource in parser.resources:
        if not resource:
            errors.append(f"{relative}: empty resource reference")
            continue
        resolve_relative(path, resource, errors, "resource")


def check_assets(errors: list[str]) -> None:
    required = {
        ROOT / "assets" / "site.css",
        ROOT / "assets" / "locale-redirect.js",
        ROOT / "assets" / "site-mark.svg",
        ROOT / ".nojekyll",
    }
    for path in required:
        if not path.is_file():
            errors.append(f"missing asset {path.relative_to(ROOT)}")
    css_path = ROOT / "assets" / "site.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        for token in (
            "#fc67aa",
            "#ce5fe8",
            "#8980f7",
            "#5a9efa",
            "focus-visible",
            "forced-colors",
            "min-height: 44px",
            "white-space: nowrap",
            ":lang(ar)",
            ":lang(zh)",
        ):
            if token not in css:
                errors.append(f"site.css: missing accessibility or Aurora token {token}")
        if re.search(r"@keyframes|\banimation\s*:|\bgray\b|\bgrey\b", css, re.I):
            errors.append("site.css: forbidden animation or neutral-grey styling")
        if re.search(r"@import|url\s*\(\s*['\"]?https?://", css, re.I):
            errors.append("site.css: remote stylesheet or asset")
    router_path = ROOT / "assets" / "locale-redirect.js"
    if router_path.is_file():
        router = router_path.read_text(encoding="utf-8")
        if TRACKING_CODE_RE.search(router):
            errors.append("locale router contains storage, tracking, or network access")
        if re.search(r"https?://", router):
            errors.append("locale router contains an external URL")
        for locale in LOCALES:
            if f'"{locale}"' not in router:
                errors.append(f"locale router omits {locale}")
    mark_path = ROOT / "assets" / "site-mark.svg"
    if mark_path.is_file():
        mark = mark_path.read_text(encoding="utf-8")
        if "<script" in mark.lower() or re.search(r"\bhref\s*=", mark, re.I):
            errors.append("site-mark.svg contains executable or external content")
        if any(provider in mark for provider in PROVIDER_NAMES):
            errors.append("site-mark.svg contains a provider identity")


def check_sitemap(errors: list[str]) -> None:
    sitemap = ROOT / "sitemap.xml"
    robots = ROOT / "robots.txt"
    if not sitemap.is_file() or sitemap.read_text(encoding="utf-8") != render_sitemap():
        errors.append("sitemap.xml is missing or stale")
    expected_robots = f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n"
    if not robots.is_file() or robots.read_text(encoding="utf-8") != expected_robots:
        errors.append("robots.txt is missing or stale")


def check_manifest(
    outputs: dict[pathlib.Path, str], errors: list[str]
) -> None:
    expected = set(outputs) | {
        ROOT / ".gitignore",
        ROOT / ".nojekyll",
        ROOT / "README.md",
        ROOT / "assets" / "locale-redirect.js",
        ROOT / "assets" / "site-mark.svg",
        ROOT / "assets" / "site.css",
        ROOT / "scripts" / "generate_site.py",
        ROOT / "scripts" / "validate_site.py",
        ROOT / "source" / "site.json",
    }
    expected.update(
        ROOT / "source" / "locales" / f"{locale}.json" for locale in LOCALES
    )
    actual: set[pathlib.Path] = set()
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_symlink():
            errors.append(f"unexpected symlink: {path.relative_to(ROOT)}")
        elif path.is_file():
            actual.add(path)
    for path in sorted(expected - actual):
        errors.append(f"missing repository file: {path.relative_to(ROOT)}")
    for path in sorted(actual - expected):
        errors.append(f"unexpected repository file: {path.relative_to(ROOT)}")


def check_text_format(errors: list[str]) -> None:
    extensions = {".css", ".html", ".js", ".json", ".md", ".py", ".svg", ".txt", ".xml"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix not in extensions and path.name not in {".gitignore", ".nojekyll"}:
            errors.append(f"unexpected binary or unreviewed file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_PUBLIC_EMAIL in text:
            errors.append(f"{path.relative_to(ROOT)}: forbidden public email")
        unauthorized_emails = set(EMAIL_RE.findall(text)) - {EMAIL}
        if unauthorized_emails:
            errors.append(
                f"{path.relative_to(ROOT)}: unauthorized email "
                f"{', '.join(sorted(unauthorized_emails))}"
            )
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        expected = "\n".join(lines) + ("\n" if lines else "")
        if text != expected:
            errors.append(
                f"{path.relative_to(ROOT)}: trailing whitespace or extra blank line at EOF"
            )


def main() -> None:
    errors: list[str] = []
    try:
        translations = load_translations()
    except SystemExit as error:
        raise SystemExit(f"FAIL: {error}") from error
    check_sources(errors, translations)
    outputs = expected_outputs(translations)
    expected_html = {path for path in outputs if path.suffix == ".html"}
    actual_html = set(ROOT.rglob("*.html"))
    if len(expected_html) != EXPECTED_PAGES or actual_html != expected_html:
        errors.append(f"HTML page set must be exactly {EXPECTED_PAGES}")
    parsed_pages = parse_pages(expected_html, errors)
    for locale in (None, *LOCALES):
        for page in PAGES:
            path = ROOT / PAGE_FILES[page] if locale is None else ROOT / locale / PAGE_FILES[page]
            parser = parsed_pages.get(path.resolve())
            if parser is None:
                errors.append(f"missing page {path.relative_to(ROOT)}")
            else:
                check_page(path, locale, page, parser, parsed_pages, errors)
    check_assets(errors)
    check_sitemap(errors)
    check_manifest(outputs, errors)
    check_text_format(errors)
    for path, expected in outputs.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            errors.append(f"generated output is stale: {path.relative_to(ROOT)}")
    if errors:
        for error in dict.fromkeys(errors):
            print(f"FAIL: {error}")
        raise SystemExit(1)
    canonical_state = (
        "staging placeholder"
        if urllib.parse.urlparse(BASE_URL).hostname.endswith(".invalid")
        else "deployment URL"
    )
    print(
        f"PASS: {EXPECTED_PAGES} pages, {len(LOCALES)} locales, exact relative links, "
        f"canonical/hreflang/sitemap, accessibility, and UsageNow privacy facts verified; "
        f"canonical={BASE_URL} ({canonical_state})."
    )


if __name__ == "__main__":
    main()
