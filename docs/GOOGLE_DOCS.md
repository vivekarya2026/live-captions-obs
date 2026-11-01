# Google Docs

Live Captions can write the original speech and the translation into Google Docs
while people speak. Each session gets its **own new doc** in your Google Drive.

## Use it

1. In the Live Captions window open **Google Docs** → **Sign in with Google** (only the first time).
   - A browser tab opens. Choose your Google account and press **Continue / Allow**.
   - If Google says *“Google hasn't verified this app”*: **Advanced → Go to Live Captions**.
   - The tab says **✓ Signed in**. Close it.
2. Press **Start writing**. A new doc *“Live Captions · 1 Nov 2026, 10:30”* appears in your
   Google Drive and the sentences are added at its end. **Open the doc** shows it.
3. **Time stamps**: untick to leave out the time in front of each line. You can switch it
   any time; it applies to the next lines.
4. **Stop writing** pauses. **New session** (in *Saving transcript*) makes the next doc.

With time stamps:

> **10:31:02 · Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa and simran.

Without:

> **Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa and simran.

What Live Captions can see: Google only lets it **see and edit the docs it created itself**
(permission *drive.file*). It can't open any of your other files. The sign-in is kept on
this computer only (`~/.livecaptions/google_account.json`). **Sign out** removes it and also
cancels the access at Google; your docs stay in your Drive.

If the internet drops for a moment, lines wait and are sent in order when it is back.
The sessions are also always saved on the computer (Documents → Live Captions).

## Problems

| The window shows… | Fix |
|---|---|
| *Google sign-in isn't set up in this version yet* | The installer was built without the Google client (maintainer: see below). |
| *Error 403: access_denied* in the browser | The Google account isn't on the test-user list (maintainer: add it, see step 4 below), or publish the app. |
| *Google access ended* | You signed out at Google, changed your password, or 7 days passed while the app is in *Testing*. Press **Sign in with Google** again. |
| *can't reach Google (offline?)* | Check the internet; lines are kept and sent later. |

Versions before 1.0.9 used an Apps Script pasted into the doc. That's no longer needed:
you can delete it in the doc (**Extensions → Apps Script**), or just leave it.

---

## Maintainer: one-time Google Cloud setup (about 10 minutes)

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
