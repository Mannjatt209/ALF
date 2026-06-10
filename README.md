# LifeLine Adult Family Home — Website

Public website for **LifeLine Adult Family Home**, a 5-bed adult family home
in Marysville, Washington, owned and operated by Manpreet Kaur.

**Live site:** https://mannjatt209.github.io/ALF/

## How this project works

- The website is a single scrolling page built with plain HTML, CSS, and
  JavaScript — no build step required.
  - `index.html` — all of the page content (the words families read)
  - `css/styles.css` — colors, fonts, and layout
  - `js/script.js` — mobile menu, contact form, footer year
- Hosting is **GitHub Pages**, served from the `gh-pages` branch.
- Publishing is automatic: every push to the default branch triggers
  `.github/workflows/deploy-pages.yml`, which syncs the content to
  `gh-pages`. Changes appear on the live site within a minute or two.

## How to update the site

Ask Claude Code (from claude.ai/code or the GitHub integration) to make the
change, or edit `index.html` directly on GitHub and commit — the site
republishes automatically either way.

## Remaining placeholders to fill in

Search `index.html` for `[` brackets:

- `[LICENSE NUMBER]` — DSHS Adult Family Home license number (appears in the
  Licensing section and the footer) — add once issued
- `[info@lifelineafh.com]` — contact email (also update `CONTACT_EMAIL` in
  `js/script.js` so the contact form goes to the right inbox)
- The italic paragraph in the About section — replace with the owner's
  personal story, background, and certifications
- Photo gallery — the Our Home section has a "photos coming soon" note

## Compliance notes

Washington licenses a 5-bed residential care home as an **Adult Family Home
(AFH)** under RCW 70.128 / WAC 388-76 (not an "Assisted Living Facility",
which is a different license type). The site uses AFH terminology and links
to DSHS, resident-rights law (RCW 70.129), and the Long-Term Care Ombudsman,
which families expect to see. Verify final wording against current DSHS
requirements before advertising.
