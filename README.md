# UsageNow: AI Usage Tracker — Support & Privacy

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
- Canonical and App Store Connect host:
  `https://alice51849.github.io/usagenow-support/` — support URL
  `<locale>/support.html`, privacy policy URL `<locale>/privacy.html`,
  marketing URL `<locale>/` for each of the 50 App Store locales
  (ASC app 6818607603).
- The public support email is wrapped in `<!--email_off-->` markers so a
  mirror behind Cloudflare Email Obfuscation would keep it intact.

To move hosts, replace only `canonical_base_url`, regenerate, and rerun both
checks. Relative navigation and assets do not depend on the host path.

## Privacy boundary represented by this site (app 1.0, 2026-10-03)

- Sign-in tokens stay in the device Keychain (`AfterFirstUnlockThisDeviceOnly`,
  not synchronizable), shared only with UsageNow's own Home Screen widget so it
  can refresh by itself; never iCloud, never Apple Watch, never the developer.
- The device talks directly to each service's own sign-in page and API over
  HTTPS (Claude, ChatGPT/Codex, GitHub Copilot, Gemini). No developer server,
  proxy, VPN or tunnel; a local loopback address receives the sign-in reply.
- Usage snapshots stay on the device (App Group) and go to the paired Apple
  Watch through WatchConnectivity, without tokens.
- No advertising, analytics, crash reporting or tracking. StoreKit (Apple)
  handles the 24-hour free trial and the one-time UsageNow Pro purchase.
