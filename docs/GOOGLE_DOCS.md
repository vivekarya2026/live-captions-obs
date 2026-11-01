# Live Captions in Google Docs

While people speak, Live Captions writes each sentence into your Google Doc:

> **10:31:02 · Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa (selfless service) and simran (remembrance of God).

A **Live Captions** sidebar in the doc has a **Start writing / Stop writing** button and
shows the last lines. You don't need OBS. Live Captions must be running on your computer
(it listens to the microphone there).

## How it works (and why the setup has a few steps)

Browsers don't allow a Google Docs page to talk directly to a program on your
computer. So the doc gets a small script of its own (Google *Apps Script*, which
runs in your Google account). The Live Captions app sends each sentence to that
script over the internet, and the script adds it to the document. Only the app
that has your secret **connection link** can write to the doc.

The audio stays on your computer; only the text is sent.

## One-time setup (about 3 minutes per document)

1. Open (or create) the Google Doc you want the captions in.
2. Menu **Extensions → Apps Script**. A new tab opens with a file `Code.gs`.
3. Delete everything in it. In the **Live Captions** window open **Google Docs** and press
   **Copy script**, then paste it into `Code.gs` (or copy
   [`LiveCaptions.gs`](../app/livecaptions/data/google-docs/LiveCaptions.gs)).
   Press **Save** (the disk icon).
4. Top right: **Deploy → New deployment**. Click the gear next to *Select type* → **Web app**.
   - *Execute as*: **Me**
   - *Who has access*: **Anyone**
   - Press **Deploy**, then **Authorize access** and choose your Google account.
   - Google warns *“Google hasn't verified this app”*: this is your own script, so click
     **Advanced → Go to … (unsafe)** → **Allow**.
5. Go back to the doc tab and **reload** the page. A new menu **Live Captions** appears
   (next to *Help*). Choose **Live Captions → Open sidebar**.
6. In the sidebar press **Copy connection link**. In the Live Captions window
   (**Google Docs** section) paste it and press **Connect**.
   The sidebar then says *App connected*.

*“Anyone” access only means the app can reach the script without signing in to
Google. Nothing can be written without the secret key in your connection link.
If you shared the link by mistake: sidebar → Security → **Make a new link**.*

## Every time (no sidebar needed)

1. Start Live Captions (or OBS) and choose the language.
2. In the Live Captions window → **Google Docs** → **Start writing**.
   A heading with the date is added to the doc, then the captions follow.
3. **Time stamps**: untick it to leave out the time (e.g. `10:31:02`) in front of each line.
   You can switch it any time, even while writing; it applies to the next lines.
4. **Stop writing** when you are done. (The sessions are also saved in
   Documents → Live Captions, as always.)

You don't need to open the doc for this. The sidebar in the doc
(**Live Captions → Open sidebar**) has the same Start/Stop button and Time stamps box,
plus the last lines, if you'd rather work from there.

With time stamps:

> **10:31:02 · Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa and simran.

Without:

> **Hindi**   आज सत्संग में सेवा और सिमरन की बात होगी।
> Today the satsang will be about sewa and simran.

### Already set up a doc before version 1.0.7?

Update its script once, so the app can start/stop it and switch time stamps:
**Extensions → Apps Script** → paste the new script (**Copy script** in the app) → **Save** →
**Deploy → Manage deployments** → ✎ (edit) → *Version*: **New version** → **Deploy**.
The connection link stays the same. Until then the app says *update the script* and you
use the sidebar as before.

Lines are added at the **end** of the document, so you can type notes above them
while they come in. If the internet drops for a moment, lines wait and are sent
in order when it is back.

## Using it in another document

The script belongs to the document it was added to. For another document, repeat
the setup, or keep one “Live Captions” document and let each session add its own
dated heading.

## Problems

| The app shows… | Fix |
|---|---|
| *That isn't a Live Captions link* | Copy the link with the sidebar's **Copy connection link** button (it starts with `https://script.google.com/` and ends with `?k=…`). |
| *the script is not deployed as a web app for "Anyone"* | Step 4 again: Deploy → Manage deployments → edit → *Who has access: Anyone*. |
| *wrong key* | The link was renewed. Copy it again from the sidebar. |
| *Google says this link doesn't exist* | The link points to a web app that isn't there (Google gave the sidebar a wrong address, or the deployment was archived). In Apps Script: **Deploy → Manage deployments** → copy the **Web app URL**. No deployment listed? Make one (step 4). Then in the doc sidebar: **App says “link not found”?** → paste it → **Save** → **Copy connection link** → in the app **Disconnect** and paste the new link. |
| *can't reach Google (offline?)* | Check the internet; lines are kept and sent later. |
| Sidebar says *One more step* | Paste the *Web app URL* from **Deploy → Manage deployments** (ends in `/exec`) into the sidebar and press Save. |
