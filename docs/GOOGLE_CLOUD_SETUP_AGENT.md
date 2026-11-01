# Task for an AI browser agent: set up "Sign in with Google" for Live Captions

## Goal

Create one Google Cloud **OAuth client of type "Desktop app"** that the Live Captions app
uses so people can press *Sign in with Google* and have captions written into Google Docs.

Done = all of these are true:

1. A Google Cloud project named **Live Captions** exists.
2. The **Google Docs API** is **enabled** in it.
3. The OAuth consent screen (Google Auth Platform) is set up: app name *Live Captions*,
   audience **External**, scope **`https://www.googleapis.com/auth/drive.file`**,
   publishing status **In production**.
4. An OAuth client of type **Desktop app** exists, and its **JSON file is downloaded**
   to the Downloads folder (name like `client_secret_….apps.googleusercontent.com.json`).

## Rules for the agent

- Use the Google account the user is already signed in with. **Never type passwords**; if a
  sign-in, 2-step check or captcha appears, stop and ask the user to do it.
- Do **not** turn on billing, add a payment method, or enable any API other than the Google Docs API.
  All of this is free.
- Do **not** add any scope other than `drive.file`.
- Do **not** paste the client secret anywhere (chat, docs, email). Only download the JSON file.
- If a screen looks different from these steps (Google renames menus often), look for the
  same words in the left menu or the search bar at the top, and say what you did instead.

## Steps

### 1. Project
1. Open <https://console.cloud.google.com/>.
2. If asked, accept the Terms of Service (country: the user's country).
3. Top bar: click the **project picker** (next to "Google Cloud") → **New project**.
4. Project name: `Live Captions`. Organization / location: leave as is → **Create**.
5. Wait for the notification, then make sure **Live Captions** is the selected project in the top bar.

✅ Check: the top bar shows **Live Captions**.

### 2. Google Docs API
1. Open <https://console.cloud.google.com/apis/library/docs.googleapis.com> (project: Live Captions).
2. Click **Enable**.

✅ Check: the page shows **API enabled** / a **Manage** button.

### 3. Consent screen (Google Auth Platform)
1. Open <https://console.cloud.google.com/auth/overview> → **Get started**
   (old menu: *APIs & Services → OAuth consent screen*).
2. **App information**: App name `Live Captions`; User support email: the user's email → **Next**.
3. **Audience**: **External** → **Next**.
4. **Contact information**: the user's email → **Next**.
5. Tick *I agree to the Google API Services: User Data Policy* → **Continue** → **Create**.

### 4. Permission (scope)
1. Left menu **Data Access** (old: *Scopes* step) → **Add or remove scopes**.
2. In the filter type `drive.file`, tick
   **`.../auth/drive.file`**: *See, edit, create, and delete only the specific Google Drive files you use with this app*.
3. **Update** → **Save** (bottom of the page).

✅ Check: under *Your non-sensitive scopes* there is exactly one: `.../auth/drive.file`.
(It must be under **non-sensitive**. If Google lists it as sensitive or restricted, stop and tell the user.)

### 5. Publish
1. Left menu **Audience** → *Publishing status: Testing* → **Publish app** → **Confirm**.

✅ Check: *Publishing status: **In production***. If Google says verification is required
before publishing, don't submit anything: stop here, and instead under **Test users → Add users**
add the team's Gmail addresses (the user will tell you), then continue.

### 6. Desktop client + JSON
1. Left menu **Clients** (old: *APIs & Services → Credentials → Create credentials → OAuth client ID*)
   → **Create client**.
2. Application type: **Desktop app**. Name: `Live Captions` → **Create**.
3. In the dialog that shows the Client ID: **Download JSON** → **OK**.

✅ Check: a file `client_secret_….json` is in the Downloads folder.

## Report back (paste this, filled in, to the Live Captions developer chat)

```
Project ID: ……………… (shown in the project picker, e.g. live-captions-123456)
Google Docs API: enabled  yes / no
Scope added: drive.file  yes / no   (listed as non-sensitive: yes / no)
Publishing status: In production / Testing (test users added: ……)
Client type: Desktop app  yes / no
JSON file name in Downloads: client_secret_………………….json
Anything that looked different or failed: ……
```

Do **not** include the client secret or the file contents in the report. The developer reads
the file from the Downloads folder.
