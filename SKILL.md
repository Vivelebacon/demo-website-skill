---
name: demo-website
description: Full prospect demo pipeline. The user runs "demo website" (or /demo-website) and pastes a prospect's URL or name; redesign their whole existing site with the scroll-craft skill (every page, same logo, same photos, same text, same page structure, new design), deploy it to Vercel, then draft the "here is the demo" reply in the mailbox the outreach went out from. Use for "demo website <url>", "build the demo for X", "X wants to see the demo", "redesign X for the prospect".
---

# Demo website

One run takes a prospect from "yes, I would like to see it" to a live redesign and a
reply waiting in Drafts. The user pastes a URL or a name; everything else is found,
not asked. Creative direction is delegated for the whole run: do not stop for
interview answers or approvals.

**Reference build:** once you have shipped one demo you are happy with, keep it as
the reference. Read its `BRIEF.md` and copy its structure (`site.css`, `site.js`,
`pages.css`, `home.css`, `home.js`, `lab/`) as the starting skeleton. Never copy its
design: the fingerprint gate forbids it.

## Fixed rules for every demo

- **Keep:** the logo, every photograph, every word of copy, every page and the
  section order inside each page. Typos stay. Nav labels stay. CTA labels stay.
- **Change:** everything visual. Layout, type, colour use, motion, interaction.
- **Every page is redesigned,** not just the home. One HTML file per original page,
  same slugs (`cleanUrls` keeps `/services` working).
- **Allowed additions:** minimal UI microcopy only (form status lines, an input
  placeholder, `aria` labels). No new marketing text, no invented numbers.
- House rules win over any reference (edit this list to your own taste): light
  palette with the client's own accent, brand + owner photo + all services visible
  in the hero, sticky header always visible, logo click returns to the top (smooth
  scroll on the home page), no side rail, no em dashes anywhere visible, client's
  own photos only (no generation unless the user asks).
- Deploy to Vercel production and commit without asking. Emails are **drafts only**.

## Step 0 · Identify the prospect

1. If the user gave a name, not a URL, and you keep a CRM: look the prospect up
   there for website, city, language, the mailbox the outreach went out from, and
   reply state. If the prospect is not in a CRM, work from the URL and ask nothing;
   the draft step will say which mailbox it needs.
2. Slug: the domain stem, e.g. `acmecoaching`. Build folder:
   `demos/<slug>-scrollcraft/`. Vercel project: `<slug>-redesign`. Demo URL:
   `https://<slug>-redesign.vercel.app` (hyphen, never a dot: a dotted subdomain
   does not exist, and a dead link is the costliest mistake in this pipeline).
3. First name for the email: from the prospect's email signature, the site's
   about/contact page, or the domain ("janecoaching" → Jane). If truly unknown,
   leave it out ("Bonjour," / "Hi,").

## Step 1 · Capture the whole existing site

Everything goes to `<build>/_src/` (raw assets) and `<build>/lab/` (notes, shots).

1. Fetch the home and read the nav + footer links to list every page. Fetch each page.
2. Extract per page, in order: sections, headings, paragraphs (with bold/italic
   spans), lists, buttons and their targets, images (full-resolution URLs; for
   Squarespace append `?format=2500w`, for Wix strip the `/v1/fill/...` transform),
   forms (field labels, required flags, submit label, success message), embedded
   video. Squarespace keeps form definitions in `data-block-json` / `formFields`.
3. Download the logo (all variants: dark, light, favicon), every photo, every texture.
   Vectorise a simple geometric logo to SVG with `cv2.findContours` + `approxPolyDP`
   on its alpha channel; keep the PNG for complex marks.
4. Brand tokens: accent/ink/background from the site CSS variables, heading and body
   faces. Pick the closest Google Font when the face is Typekit or custom.
5. Full-page screenshots of every live page (`scripts/full.mjs <live-url> 1440 900 lab/live <pages>`)
   and read them: that is the structure you must keep.

## Step 2 · Design with scroll-craft

Load your design-research skill if you have one, then `scroll-craft`
(https://github.com/nateherkai/scroll-craft), and follow scroll-craft end to end
with these overrides:

- The brief is **self-authored under explicit creative delegation** (the user's
  standing instruction is this skill). Write `BRIEF.md` with: the fixed rules above,
  the evidence from Step 1, the eight topics authored, a named grammar with real
  constraints, the feeling curve, the one peak, the tell-someone sentence, the
  signature move, the score table, and a short plan for each inner page.
- Run the fingerprint gate against your scroll-craft workspace `FINGERPRINTS.md`
  (4 of 6 against every row). Read the "What the next build must avoid" line of each
  recent row. The signature move must come from this brand (its logo geometry, its
  tagline, its own photo), not from the last build.
- Structure is fixed by the client, so the grammar and the devices change how the
  same sections behave, never which sections exist.
- Vanilla engine (`scrollcraft.js/.css` copied untouched), plain multi-page HTML,
  page-local JS for bespoke scenes.

## Step 3 · Build

- Shared: `site.css` (tokens, header, menu, footer, buttons, frames, entrances),
  `site.js` (mounts the engine, header state, menu, logo-to-top, entrances, form),
  `pages.css` for inner pages, `home.css`/`home.js` for the home's bespoke scenes.
- Scaffolding inner pages from a one-shot script is fine; afterwards the HTML files
  are the source. Say so in `BRIEF.md`.
- Contact forms: `mailto:` hand-off to the client's address with `method="post"`,
  validation, and a status line that says plainly the mail app opens and nothing is
  sent until they press send. Never fake a success.
- Shops and booking tools: link to the client's existing product/booking pages.

### Pitfalls that have already cost a round

- **Never set `position` on a `[data-sc-stage]` element.** The engine makes it
  `sticky`; `position: relative` in your CSS silently kills every pin.
- The peak must keep the largest `data-sc-span` on the page. If the hero grows, grow
  the peak with it.
- Layered hero from one photo: trace each silhouette with a DP edge path (coarse
  gradient first, then refine on the fine one), rebuild each plate under the next
  silhouette (sky: fitted vertical gradient; distant haze: flat per-column colour;
  textured slopes: mirror-tile ~110px), clear leftover dark specks above traced
  lines, then **look at the final scroll position**: seams only show at the end of
  the travel.
- Person cutouts: rembg `u2net_human_seg`, erode the matte ~2px and decontaminate
  edge colours, or the original wall shows as a halo. Crop where a foreground plane
  or base band hides the cut.
- Anything with `white-space: nowrap` inside a grid breaks phone layouts; let buttons
  wrap below 520px and use `minmax(0, 1fr)`.
- Skewed decorative blocks overflow the viewport on phones: `overflow-x: clip` on
  their section.
- A replaced image keeps its old bytes on phones for a week (`/assets` cache header):
  new art gets a new filename (`-v2`).
- `.prose p { margin: 0 }` beats `.prose > * + *`; write the spacing rule as
  `.prose > * { margin: 0 } .prose > * + * { margin-top }`.

## Step 4 · Verify

Serve locally (`node <scroll-craft>/scripts/serve.mjs --root . --port 4610`) and use
`scripts/snap.mjs` / `scripts/full.mjs` from this skill. Both resolve
`playwright-core` from the folder you run them in or any parent of it, so one
`npm i playwright-core` at the project root covers every build under it.

- Desktop 1440x900 at several positions inside every pinned act, phone 390x844 and
  360x640, reduced motion. Read every sheet; fix and reshoot.
- Full-page captures of every inner page at 1440 and 390: no overflow, no clipped
  text, no empty grid cells.
- scroll-craft harness: no dead scroll, no console errors, no failed requests.
- Contrast of text over imagery measured on composited pixels (hide the text, read
  the pixels under it); body 4.5:1, large 3:1.
- Functional: the signature interaction end to end, form validation messages, menu
  open/Escape/focus, logo to top, anchors from the hero services.
- Grep the build for em and en dashes (U+2014, U+2013): zero visible.

## Step 5 · Ship

1. `vercel.json`: `cleanUrls`, `buildCommand: null`, `outputDirectory: "."`, 7-day
   cache on `/assets`. `.vercelignore`: `lab/ _src/ node_modules/ BRIEF.md`.
2. `vercel link --yes --project <slug>-redesign` then `vercel deploy --prod --yes`.
3. Smoke-test the **exact URL you will send**: every page 200, key assets 200, `lab/`
   and `BRIEF.md` 404, one live browser load with no console errors.
4. Git repo in the build (`git init -b main`), commit with `-F <file>` (never a
   PowerShell here-string), `gh repo create <github-user>/<slug>-redesign --private --source . --push`,
   `vercel git connect --yes`. Later edits: commit and push to `main`, which redeploys.
   Keep the demo repo **private**: it holds the prospect's logo, photos and copy.
5. Append the fingerprint row to your workspace `FINGERPRINTS.md` (all six
   dimensions, world, port, palette, type, what it shares, what the next build must
   avoid).

## Step 6 · Draft the reply

```bash
python scripts/draft_demo_reply.py <prospect-email> --mailbox <alias> --url https://<slug>-redesign.vercel.app --first-name <FirstName>
```

It checks the URL answers, finds the prospect's latest email in the outreach mailbox,
renders the "here is the demo" template in the contact's language (`--lang fr|en`)
with that mailbox's signature, saves a threaded draft in that mailbox's Drafts
folder and reads it back. It never sends. Run it with `--dry-run` first if anything
about the thread looks unusual. Mailboxes are configured in `.env` (see
`.env.example`).

When the prospect answered from another address than the one you wrote to (a
personal mailbox instead of `info@`), pass it with `--to <their-address>`: the reply
is looked up from that sender and the draft goes to it. Some IMAP servers only match
a `FROM` search on the full address; a domain fragment returns nothing.

With a CRM connected (`DEMO_CRM_DIR`, see the README), `<prospect-email>` can be
anything the CRM resolves, the mailbox and language come from the contact, and the
script logs the prospect's reply and the demo URL.

Show the draft text in the final message. Tell the user to say when it is sent so
the demo can be marked sent.

## Final report (short)

Live URL (the exact one) · pages rebuilt · the design idea in two lines · the
signature move in one · the few microcopy additions · what was verified and what was
not (real phone, Safari) · the draft (mailbox, thread, full text) · local path of the
build folder.
