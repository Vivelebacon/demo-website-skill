# demo-website (agent skill)

An agent skill for web designers who sell redesigns. Give the agent a prospect's
website; it rebuilds every page with a new design, puts it live, and leaves the
"here is the demo" reply waiting in your Drafts folder.

One run does this:

1. **Captures** the whole existing site: every page, the logo, the photos, the
   copy, the forms, the brand colours and fonts.
2. **Redesigns** every page with the
   [scroll-craft](https://github.com/nateherkai/scroll-craft) skill. The logo, the
   photos, the words and the page structure stay. Everything visual changes.
3. **Verifies** the result in a headless browser on desktop, phone and reduced
   motion.
4. **Deploys** to Vercel and smoke-tests the exact URL that will be sent.
5. **Drafts** the reply in the mailbox your outreach went out from, threaded under
   the prospect's last email. It never sends.

The full procedure is in [SKILL.md](SKILL.md).

## Install

Copy the folder into your agent's skill directory and keep `scripts/` next to
`SKILL.md`:

| Agent | Where |
| --- | --- |
| Claude Code | `<project>/.claude/skills/demo-website/` or `~/.claude/skills/demo-website/` |
| Codex | `<project>/.agents/skills/demo-website/` |
| Anything else | leave it in the workspace and tell the agent to read `SKILL.md` and follow it |

With git, for Claude Code (this skill plus the scroll-craft skill it needs):

```bash
git clone https://github.com/Vivelebacon/demo-website-skill ~/.claude/skills/demo-website
git clone https://github.com/Vivelebacon/scroll-craft-skill ~/.claude/skills/scroll-craft
```

Then say `demo website https://prospect-site.example`.

## Requirements

| | Why |
| --- | --- |
| The **scroll-craft** skill | the design method, the scroll engine and its verification harness |
| **Node 18+**, `playwright-core`, Chrome | `scripts/snap.mjs` and `scripts/full.mjs` (run `npm i playwright-core` at your project root) |
| **Vercel CLI**, logged in | the deploy |
| **GitHub CLI** (`gh`), logged in | optional: a private repo per demo, connected to Vercel |
| **Python 3.9+** | `scripts/draft_demo_reply.py`, standard library only |
| An **IMAP mailbox** | the draft reply |

Set `CHROME` if Chrome is not in its default location.

## The scripts

```bash
# Full-page capture of each page after walking it, plus horizontal overflow
node scripts/full.mjs <base-url> <width> <height> <out-prefix> [page ...]

# Screenshots at chosen scroll positions, with console and network errors
node scripts/snap.mjs <base-url> <page> <width> <height> <out-prefix> [reduced|-] [pos ...]

# The "here is the demo" reply, saved as a draft
python scripts/draft_demo_reply.py prospect@their-site.example --mailbox main \
  --url https://their-site-redesign.vercel.app --first-name Jane --dry-run
```

### Mail setup

Copy `.env.example` to `.env` (the script reads `./.env`, or the file named by
`DEMO_ENV_FILE`) and fill in one block per mailbox alias: `<ALIAS>_EMAIL`,
`<ALIAS>_PASSWORD`, `<ALIAS>_IMAP_HOST`, `<ALIAS>_SIGNATURE`. Start with
`--dry-run`: it logs in, finds the thread and prints the draft without saving
anything.

The built-in templates are French and English (`--lang fr|en`). Edit `FALLBACK` in
the script to change the wording.

### CRM hook (optional)

Set `DEMO_CRM_DIR` to a folder containing `scripts/crm.py` and the script uses it
to resolve the contact and to log what happened. The contract:

| Command | Must do |
| --- | --- |
| `crm.py show <ident>` | print JSON `{"contact": {"email", "name", "language", "last_mailbox", "last_inbound_at"}}` |
| `crm.py template --lang <xx> --step 2` | print JSON `{"body": "..."}` using `{{prenom}}`, `{{demo_url}}`, `{{signature}}` |
| `crm.py reply <ident> --body <text> --mailbox <alias>` | log the prospect's reply |
| `crm.py demo <ident> --url <url>` | log the demo URL |

No CRM is included. Without one the script works from the email address you pass.

## Before you use it on real prospects

- A demo reuses the prospect's logo, photos and text. Keep demo repositories
  private and take a demo offline if the prospect asks.
- The mail step creates drafts only, by design. Read each one before you send it.
- The "House rules" list in `SKILL.md` is one designer's taste. Edit it.

## Licence

MIT. See [LICENSE](LICENSE).
