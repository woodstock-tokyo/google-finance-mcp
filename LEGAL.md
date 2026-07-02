# Legal, usage, and contribution policy

This document explains how users, contributors, maintainers, packagers, and
downstream projects should use and contribute to this repository responsibly.
It is not legal advice. If you need a legal opinion for your organization,
commercial product, trading workflow, or public service, consult a qualified
lawyer.

## Short version

This project is intended for local, personal, manually configured,
user-initiated use. It is an unofficial execution layer for endpoints that are
advertised inside Google Finance web pages loaded by the user, or invoked by
those loaded pages during the user's manual interaction with visible Google
Finance UI features.

Do not use or contribute to this project as a hosted market-data API, shared
proxy, crawler, scheduled data puller, data warehouse, data redistribution
service, trading system, or way to bypass Google or data-provider controls.

Open-source contributors are welcome, but contributions must preserve this
scope.

## Unofficial status

This project is not affiliated with, endorsed by, sponsored by, or supported by
Google. "Google", "Google Finance", and related names are used descriptively to
identify the public web pages this local tool interacts with.

Do not use Google logos, icons, product styling, screenshots, or wording that
implies affiliation, certification, partnership, sponsorship, or endorsement.

## Sources contributors should review

Before making a release, packaging this project, or contributing features that
change how it accesses Google Finance, review the current versions of:

- Google Terms of Service:
  <https://policies.google.com/terms>
- Google Finance disclaimer:
  <https://www.google.com/googlefinance/disclaimer/>
- GOOGLEFINANCE Help:
  <https://support.google.com/docs/answer/3093281>
- Google APIs Terms of Service:
  <https://developers.google.com/terms>
- Google robots.txt:
  <https://www.google.com/robots.txt>
- Google Brand Resource Center:
  <https://about.google/brand-resource-center/guidance/>

These sources can change. The project should adapt if the rules change.

## Intended use

Acceptable use is narrow:

- running the MCP server locally on a user's own machine;
- manually configuring it in an MCP client;
- making user-initiated queries for personal experimentation or research;
- inspecting mappings advertised by the Google Finance page currently fetched;
- calling documented, user-visible page features that are invoked by the loaded
  page during the user's manual interaction with Google Finance;
- using returned data transiently for the user's local request.

This repository does not grant any license to Google Finance, Google services,
exchange data, news, analyst ratings, financial statements, or any other data
returned by Google Finance.

## Uses this project does not support

Do not use this project for:

- hosted APIs, public endpoints, SaaS services, shared proxies, or bots;
- scheduled polling, bulk ticker collection, crawling, or database building;
- storing, mirroring, reselling, transmitting, or redistributing returned data;
- professional market-data access without appropriate data-provider licenses;
- trading execution, trading advice, valuation reports, compliance reporting,
  or regulated financial workflows;
- account automation, portfolio/watchlist scraping, or access to non-public
  Google account data;
- evading rate limits, blocks, CAPTCHAs, consent screens, auth controls, or
  other protective measures.

If you need those use cases, use a licensed market-data provider or obtain
written permission from the relevant rights holders.

## Data handling rules

Users and downstream projects are responsible for their own legal compliance.
At a minimum:

- do not include live Google Finance responses in issues, pull requests,
  examples, tests, release artifacts, datasets, or documentation;
- do not commit cached finance data or generated databases;
- do not remove or obscure source attribution or legal notices;
- do not imply the returned data is accurate, complete, timely, or licensed for
  trading or redistribution;
- treat returned data as informational only and verify prices with licensed
  sources before any transaction.

## Contribution rules

Contributions should make the local execution layer safer, clearer, and more
transparent. Good contributions include:

- parser fixes for mappings advertised in fetched pages;
- narrowly scoped helpers for user-visible page features when their render-time
  requests are documented, low-volume, user-initiated, and clearly caveated;
- defensive error handling and fail-closed behavior;
- cache-header respecting behavior;
- documentation that clarifies limits, setup, or compliance;
- tests using synthetic fixtures rather than copied live market data;
- changes that reduce default request volume or improve user control.

Do not contribute:

- CAPTCHA solving, proxy rotation, ban avoidance, account automation, cookie
  extraction, or credential handling;
- stealth headers, identity masking, or behavior meant to defeat enforcement;
- background polling, broad symbol discovery, bulk crawlers, or data warehousing;
- hosted-server modes that expose Google Finance data to multiple users;
- live Google Finance payloads, screenshots, logos, copied UI assets, or
  third-party market-data fixtures;
- code that stores, republishes, sublicenses, or redistributes returned data;
- claims that the project is official, endorsed, stable, production-grade, or
  suitable for trading.

Maintainers may close issues or pull requests that violate this policy.

## Maintainer policy

Maintainers should keep the project aligned with local, personal,
user-initiated operation:

- keep defaults conservative and cache-aware;
- avoid features that increase request volume without explicit user action;
- fail closed when mappings are missing or responses indicate blocking;
- document known legal and operational risks honestly;
- remove or disable functionality after a credible rights-holder complaint,
  legal notice, or clear change in applicable terms;
- keep this document linked prominently from the README.

## Packaging and distribution

If you redistribute this project through a package registry, fork, container,
plugin bundle, or operating-system package:

- include this `LEGAL.md` unchanged or with stricter terms;
- describe the project as unofficial and local-only;
- do not add hosted service defaults;
- do not bundle cached Google Finance responses or market data;
- do not use Google branding except plain-text descriptive references;
- preserve repository copyright and license notices.

## No investment advice

This project provides software plumbing only. It does not provide financial,
investment, legal, tax, or trading advice. Google Finance data may be delayed,
incomplete, inaccurate, unavailable, or subject to third-party restrictions.
Users are solely responsible for their own decisions and for verifying data with
licensed sources.

## Release checklist

Before a public release, maintainers should verify:

- [ ] README identifies the project as unofficial and local-only.
- [ ] `LEGAL.md` is present and linked from the README.
- [ ] No live Google Finance responses are committed.
- [ ] No Google logos, icons, screenshots, or copied UI assets are included.
- [ ] Tests use synthetic data or minimal hand-written fixtures.
- [ ] Defaults are low-volume, manual, and cache-aware.
- [ ] No anti-blocking, proxy, CAPTCHA, credential, or account automation
      features are present.
- [ ] Package metadata does not imply official Google affiliation.
- [ ] A repository code license is present and clearly applies only to this
      project's code, not to data returned by Google Finance.

## Recommended public notice

Use this notice in README files, package pages, and forks:

> This is an unofficial local tool and is not affiliated with, endorsed by, or
> sponsored by Google. It does not grant rights to Google Finance data or any
> third-party market data. Intended use is personal, manually configured,
> user-initiated execution only. Do not use it as a hosted API, shared proxy,
> crawler, scheduled data puller, datastore, trading system, or redistribution
> service. Users and downstream projects are responsible for complying with
> Google terms and all applicable data-provider licenses.
