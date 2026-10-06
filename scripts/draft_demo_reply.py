"""
Draft the "here is the demo" reply for a prospect, threaded under their last email,
in the mailbox the outreach went out from. Never sends.

    python draft_demo_reply.py <ident> --url <demo_url> --mailbox <alias>
                               [--first-name Jane] [--to other@address] [--lang fr|en]
                               [--dry-run] [--no-log]

<ident> is the prospect's email address. With a CRM connected (DEMO_CRM_DIR) it is
anything the CRM's `show` command accepts (email, domain, name), and --mailbox and
--lang default to what the CRM knows about the contact.

Configuration comes from environment variables, or from a .env file (the one named
by DEMO_ENV_FILE, else ./.env). For a mailbox alias `main`:

    MAIN_EMAIL, MAIN_PASSWORD (or MAIN_APP_PASSWORD), MAIN_IMAP_HOST, MAIN_SIGNATURE

What it does:
  1. Resolves the contact (CRM if connected, else the email you passed).
  2. Checks the demo URL answers 200 (a typo in the link is the costliest mistake here).
  3. Finds the prospect's latest email in that mailbox's INBOX (falls back to our own
     outreach in Sent if they have not replied) for In-Reply-To / References / Subject.
  4. Renders the step-2 template for the contact's language with the mailbox signature.
  5. Appends it to the mailbox's Drafts folder over IMAP and reads it back.
  6. With a CRM: logs the inbound reply (if not logged yet) and the demo URL.
"""
import argparse, email, imaplib, json, os, re, subprocess, sys, time, urllib.request
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid, parsedate_to_datetime

CRM = None  # set from DEMO_CRM_DIR in main()

FALLBACK = {
    'en': ("Hi {{prenom}},\n\nHere it is: {{demo_url}}\n\nLet me know what you think, any feedback is welcome.\n\n"
           "And if you like it, we can jump on a call to talk it through. Just tell me a slot that suits you this week.\n\n"
           "Have a great day,\n{{signature}}"),
    'fr': ("Bonjour {{prenom}},\n\nLe voici : {{demo_url}}\n\nDites-moi ce que vous en pensez, tout feedback est le bienvenu.\n\n"
           "Et si ça vous plaît, on peut s'appeler au téléphone pour en discuter. Vous me dites un créneau qui vous arrange cette semaine.\n\n"
           "Bonne journée,\n{{signature}}"),
}
SUBJECT = {'en': 'I redesigned your website', 'fr': "j'ai refait votre site"}


def crm(*args):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, os.path.join(CRM, 'scripts', 'crm.py'), *args],
                       capture_output=True, text=True, encoding='utf-8', env=env, cwd=CRM)
    if r.returncode != 0:
        raise SystemExit(f'crm {" ".join(args)} failed:\n{r.stderr or r.stdout}')
    return r.stdout


def crm_json(*args):
    out = crm(*args)
    return json.loads(out[out.index('{') if out.lstrip().startswith('{') else out.index('['):])


def load_env():
    """Real environment variables win over the .env file."""
    env = {}
    path = os.environ.get('DEMO_ENV_FILE') or os.path.join(os.getcwd(), '.env')
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    env.update(os.environ)
    return env


def mailbox_config(env, box):
    """(imap host, sender address, password, signature) for a mailbox alias."""
    key = re.sub(r'\W', '_', box).upper()
    sender = env.get(f'{key}_EMAIL')
    pwd = env.get(f'{key}_PASSWORD') or env.get(f'{key}_APP_PASSWORD')
    if not sender or not pwd:
        raise SystemExit(f'Mailbox {box!r} is not configured: set {key}_EMAIL and {key}_PASSWORD '
                         f'(or {key}_APP_PASSWORD) in the environment or the .env file.')
    host = env.get(f'{key}_IMAP_HOST')
    if not host and sender.lower().endswith(('@gmail.com', '@googlemail.com')):
        host = 'imap.gmail.com'
    if not host:
        raise SystemExit(f'Set {key}_IMAP_HOST (the IMAP server of {sender}).')
    sig = env.get(f'{key}_SIGNATURE') or env.get('DEMO_SENDER_NAME') or ''
    return host, sender, pwd, sig.replace('\\n', '\n')


def text_of(m):
    parts = m.walk() if m.is_multipart() else [m]
    for p in parts:
        if p.get_content_type() == 'text/plain':
            return p.get_payload(decode=True).decode(p.get_content_charset() or 'utf-8', 'replace')
    for p in (m.walk() if m.is_multipart() else [m]):
        if p.get_content_type() == 'text/html':
            return re.sub(r'<[^>]+>', ' ', p.get_payload(decode=True).decode(p.get_content_charset() or 'utf-8', 'replace'))
    return ''


def fresh_part(body):
    """The prospect's own words, without the quoted outreach under them."""
    keep = []
    for line in body.splitlines():
        if line.startswith('>') or re.match(r'^(Le |On ).+(a écrit|wrote)\s*:?\s*$', line.strip()):
            break
        keep.append(line)
    return '\n'.join(keep).strip()


def folders(imap):
    r"""(flags, name) for every folder, from lines like (\HasNoChildren \Drafts) "/" "[Gmail]/Drafts"."""
    typ, data = imap.list()
    out = []
    for raw in data or []:
        line = raw.decode(errors='replace')
        m = re.match(r'\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>.+)$', line)
        if m:
            out.append((m['flags'], m['name'].strip().strip('"')))
    return out


def pick(imap, flag, candidates):
    for line, name in folders(imap):
        if flag and flag in line:
            return name
    names = [n for _, n in folders(imap)]
    for c in candidates:
        if c in names:
            return c
    return candidates[0]


def main():
    global CRM
    ap = argparse.ArgumentParser()
    ap.add_argument('ident')
    ap.add_argument('--url', required=True)
    ap.add_argument('--first-name', default='')
    ap.add_argument('--mailbox', help='mailbox alias, configured as <ALIAS>_EMAIL / <ALIAS>_PASSWORD')
    ap.add_argument('--to', help="the prospect's other address, when they write or want the demo somewhere else than the address you wrote to")
    ap.add_argument('--lang', help='template language, fr or en (default: the CRM contact language, else fr)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-log', action='store_true')
    a = ap.parse_args()

    env = load_env()
    CRM = env.get('DEMO_CRM_DIR') or None

    if CRM:
        c = crm_json('show', a.ident)['contact']
    elif '@' in a.ident:
        c = {'email': a.ident.strip(), 'name': a.ident.strip()}
    else:
        raise SystemExit('Without a CRM (DEMO_CRM_DIR), <ident> must be the prospect email address.')
    to = c['email']
    box = a.mailbox or c.get('last_mailbox')
    if not to:
        raise SystemExit(f"{c['name']} has no email in the CRM.")
    if not box:
        raise SystemExit('Pass --mailbox <alias>.')
    lang = (a.lang or c.get('language') or 'fr')[:2]
    host, sender, pwd, sig = mailbox_config(env, box)

    try:
        code = urllib.request.urlopen(urllib.request.Request(a.url, method='GET', headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).status
    except Exception as e:
        raise SystemExit(f'Demo URL does not answer: {a.url} ({e}). Fix the link before drafting.')
    if code != 200:
        raise SystemExit(f'Demo URL returned {code}: {a.url}')

    imap = imaplib.IMAP4_SSL(host, 993)
    imap.login(sender, pwd)
    inbox = 'INBOX'
    sent = pick(imap, '\\Sent', ['INBOX.Sent', 'Sent', '[Gmail]/Sent Mail', '[Gmail]/Messages envoy&AOk-s'])
    drafts = pick(imap, '\\Drafts', ['INBOX.Drafts', 'Drafts', '[Gmail]/Drafts', '[Gmail]/Brouillons'])

    def latest(folder, crit):
        imap.select(f'"{folder}"' if ' ' in folder or '/' in folder else folder, readonly=True)
        typ, d = imap.search(None, crit)
        ids = d[0].split() if d and d[0] else []
        if not ids:
            return None
        typ, md = imap.fetch(ids[-1], '(RFC822)')
        return email.message_from_bytes(md[0][1])

    # the thread is anchored on the address we wrote to; the reply may come from, or go to, another one
    dest = (a.to or to).strip()
    theirs = latest(inbox, f'(FROM "{dest}")') or (latest(inbox, f'(FROM "{to}")') if dest != to else None)
    ours = latest(sent, f'(TO "{to}")')
    anchor = theirs or ours
    if anchor is None:
        print(f'! No thread with {to} in {box}: drafting a fresh email.')
    elif theirs is None:
        print(f'! {to} has not replied in {box}: threading under our outreach instead.')

    subj = str(make_header(decode_header(anchor['Subject']))) if anchor and anchor['Subject'] else SUBJECT.get(lang, SUBJECT['fr'])
    if anchor is not None and not re.match(r'^(re|aw|tr)\s*:', subj, re.I):
        subj = 'Re: ' + subj

    tpl = None
    if CRM:
        try:
            tpl = crm_json('template', '--lang', lang, '--step', '2')['body']
        except SystemExit:
            pass
    tpl = tpl or FALLBACK.get(lang, FALLBACK['fr'])
    first = a.first_name.strip()
    body = tpl.replace('{{demo_url}}', a.url).replace('{{signature}}', sig)
    body = body.replace(' {{prenom}},', f' {first},' if first else ',').replace('{{prenom}}', first)

    m = MIMEText(body, 'plain', 'utf-8')
    name = env.get('DEMO_SENDER_NAME', '').strip()
    m['From'] = formataddr((name, sender)) if name else sender
    m['To'] = str(make_header(decode_header(theirs['From']))) if theirs else dest
    m['Subject'] = subj
    m['Date'] = formatdate(localtime=True)
    m['Message-ID'] = make_msgid(domain=sender.split('@')[1])
    if anchor is not None and anchor['Message-ID']:
        refs = ' '.join(x for x in [(anchor['References'] or '').strip(), anchor['Message-ID'].strip()] if x)
        m['In-Reply-To'] = anchor['Message-ID'].strip()
        m['References'] = refs

    print(f'--- draft · {box} ({sender}) -> {dest} · {subj}\n{body}\n---')
    if theirs is not None:
        print("Their message:\n" + fresh_part(text_of(theirs)) + '\n---')
    if a.dry_run:
        imap.logout()
        return

    typ, _ = imap.append(f'"{drafts}"' if ' ' in drafts or '/' in drafts else drafts, r'(\Draft)',
                         imaplib.Time2Internaldate(time.time()), m.as_bytes())
    if typ != 'OK':
        raise SystemExit(f'IMAP append to {drafts} failed')
    back = latest(drafts, f'(HEADER Message-ID "{m["Message-ID"]}")')
    imap.logout()
    print(f'Draft saved in {box} · {drafts}' + (' (read back OK)' if back is not None else ' (could not read back)'))

    if a.no_log or not CRM:
        return
    if theirs is not None:
        when = parsedate_to_datetime(theirs['Date']) if theirs['Date'] else None
        last_in = c.get('last_inbound_at')
        if not last_in or (when and when.isoformat() > last_in):
            crm('reply', a.ident, '--body', fresh_part(text_of(theirs))[:500] or '(reply)', '--mailbox', box)
            print('CRM: reply logged')
    crm('demo', a.ident, '--url', a.url)
    print('CRM: demo logged (not marked sent; run `crm.py demo <ident> --url <url> --sent` once it is sent)')


if __name__ == '__main__':
    main()
