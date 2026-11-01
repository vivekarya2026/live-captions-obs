# Google Docs

Live Captions can write the original speech and the translation into Google Docs
while people speak. Each session gets its **own new doc** in your Google Drive.

## Way 1 (simplest): a script in your doc

Once per doc, about 2 minutes. No Google Cloud, no test list, no signing in again later.

1. Open the Google Doc you want the captions in.
2. **Extensions → Apps Script**. Delete everything there. In the Live Captions window
   (**Google Docs**) press **Copy script**, paste it, press **Save** (disk icon).
3. **Deploy → New deployment** → gear icon → **Web app**.
   *Execute as*: **Me** · *Who has access*: **Anyone** → **Deploy**.
4. **Authorize access** → your account. Google warns *“hasn't verified this app”*: it's your own
   script, so **Advanced → Go to … (unsafe) → Allow**.
5. Copy the **Web app URL** (ends in `/exec`) → paste it in the Live Captions window → **Connect**.
   It says *Connected to “your doc”*.

Each time: **Start writing** adds a dated heading, then the captions at the end of the doc.
**Stop writing** when done. Untick **Time stamps** to leave out the times.

Keep the Web app URL private: whoever has it can add text to that doc.
On another computer: paste the same Web app URL there (write from one computer at a time).

## Way 2: Sign in with Google

Under **Or: Sign in with Google** in the window. A new doc for each session; no script.
Your Gmail must be on the app's test list (ask the maintainer), and Google asks you to sign in
again every 7 days. Live Captions can see and edit only the docs it creates.

## How it looks

With time stamps:

> **10:31:02 · Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa and simran.

Without:

> **Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa and simran.

If the internet drops for a moment, lines wait and are sent in order when it is back.
Sessions are also always saved on the computer (Documents → Live Captions).

## Problems

| The window says… | Fix |
|---|---|
| *That's the doc's own link* / *the Apps Script editor link* / *the test URL (/dev)* | Copy the **Web app URL**: in Apps Script **Deploy → Manage deployments** → Web app → URL (ends in `/exec`). |
| *Google can't find this web app* | The deployment was deleted or the URL is cut off. Copy it again from **Manage deployments**, or make a **New deployment**. |
| *Google asks to sign in* / *Google refused* | **Manage deployments → ✎**: *Execute as* **Me**, *Who has access* **Anyone** → **Deploy**. Work/school accounts may not allow “Anyone”; use a personal Gmail doc or Way 2. |
| *The doc has an older Live Captions script* | Paste the new script (**Copy script**) → **Save** → **Manage deployments → ✎ → Version: New version → Deploy**. The URL stays the same. |
| *Open (or reload) the Google Doc once* | Open the doc in the browser once, then press **Connect** again. |
| *can't reach Google (offline?)* | Check the internet; lines are kept and sent later. |
| Way 2: *Error 403: access_denied* | Your Gmail isn't on the test list: ask the maintainer to add it. |
| Way 2: *Google access ended* | Press **Sign in with Google** again (every 7 days while the app is in Testing). |

Docs set up with version 1.0.7 or 1.0.8 need the new script once (row *older script* above).

---

## Maintainer: Way 2 setup, once (about 10 minutes)

The app needs one OAuth client ("Desktop app") that every installation uses.

1. [console.cloud.google.com](https://console.cloud.google.com/) → project picker → **New project**
   → name *Live Captions* → **Create**.
2. **APIs & Services → Library** → search **Google Docs API** → **Enable**.
3. **APIs & Services → OAuth consent screen** (Google Auth Platform) → **Get started**:
   app name *Live Captions*, your support email, audience **External**, contact email → **Create**.
4. **Data access** → **Add or remove scopes** → tick `.../auth/drive.file` → **Update → Save**.
   **Audience** → **Test users** → add the Google accounts of your team (up to 100).
   *(Or press **Publish app** so anyone can sign in. `drive.file` needs no Google review;
   users then see the "unverified app" note until you verify the app's branding.)*
5. **Clients** (Credentials) → **Create client** → type **Desktop app** → name *Live Captions* →
   **Create** → **Download JSON**.
6. Give the JSON to the builds, as a GitHub secret:
   ```bash
   gh secret set GOOGLE_OAUTH_CLIENT -R vivekarya2026/live-captions-obs < ~/Downloads/client_secret_*.json
   ```
   The next release bundles it. To try it before that, copy the file to
   `~/.livecaptions/google_oauth_client.json` and restart Live Captions.

For a Desktop app client, Google treats the "secret" as not secret: it is fine inside the
installer. Access is still protected by each user's own sign-in (with PKCE).
