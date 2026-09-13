# UsageNow: AI Usage — Support & Privacy

Independent, deployment-ready static support and privacy site for UsageNow.

## Source of truth

- `source/site.json` — exact Apple locale list, product identity, contact email,
  policy date, and the single canonical base URL.
- `source/locales/*.json` — native-language copy for all 50 official Apple
  locales.
- `scripts/generate_site.py` — deterministic HTML, sitemap, and robots
  generator.
- `scripts/validate_site.py` — fail-closed locale, privacy, link, accessibility,
  security, and reproducibility checks.
- `assets/` — local Aurora Pearl presentation and a UsageNow-specific vector
  mark. The published pages load no remote assets.

Generated HTML must not be edited by hand.

## Generate and validate

```sh
python3 scripts/generate_site.py
python3 scripts/generate_site.py --check
python3 scripts/validate_site.py
```

The generated site contains 153 HTML pages: three English `x-default` fallback
pages plus `index.html`, `support.html`, and `privacy.html` for every official
Apple locale. Every page has a self-canonical URL, exact-50 `hreflang`
alternatives plus `x-default`, localized metadata, semantic landmarks, and an
exact-50 language selector.

## Deployment

- GitHub repository `alice51849/usagenow-support` (public), served by GitHub
  Pages from the root of `main`.
- Origin: `https://alice51849.github.io/usagenow-support/`. This is the host
  registered in App Store Connect as the support and privacy policy URL.
- Canonical host: `https://open.cait518.cc/usagenow-support/`, a Cloudflare
  tunnel mirror of the origin that serves the same bytes. Every `canonical`,
  `og:url`, `hreflang`, sitemap, and robots URL uses this host through
  `canonical_base_url` in `source/site.json`.
- The canonical host applies Cloudflare Email Obfuscation, so the generator
  wraps the public support email in `<!--email_off-->` markers to keep the
  visible address and the `mailto:` link intact; the validator fails if any
  address falls outside those markers.

To move hosts, replace only `canonical_base_url`, regenerate, and rerun both
checks. Relative navigation and assets do not depend on the host path.

## Privacy boundary represented by this site

- Provider credentials stay in the main app's local, non-synchronizable
  Keychain with `AfterFirstUnlockThisDeviceOnly` protection.
- On a user-requested refresh, the app contacts the selected provider's
  documented official API directly. There is no UsageNow developer relay.
- The developer does not automatically receive credentials, usage values, or
  provider responses.
- Optional sync stores only minimized normalized records in the user's private
  CloudKit database. Widget and Watch surfaces receive secret-free snapshots.
- Apple handles product loading, purchase, and Restore through StoreKit.
- There is no developer account system, advertising, third-party analytics,
  tracking, cookie extraction, dashboard HTML scraping, or private endpoint use.
- Security diagnostics exclude credentials, slugs, full URLs, request and
  response bodies, and headers.
- Full deletion covers local storage, Keychain, App Group, Widget, Watch,
  private CloudKit records, and the trial anchor. Only a non-identifying
  CloudKit deletion generation remains to prevent offline resurrection.

Provider names appear only as compatibility identifiers. UsageNow is independent
and is not endorsed, sponsored, or affiliated with those providers.
