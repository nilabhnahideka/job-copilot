# Job Copilot for Chrome

A Chrome side panel that works on the job page you're looking at:

1. Click the Job Copilot icon. A panel opens beside the page.
2. Click **Read this job**. It reads the job description from the page (or exactly the text you selected), and you can edit it.
3. Click **Analyse my fit**. You see each step live, then:
   - your **fit score**, with a bar showing each requirement (covered / partly / missing)
   - **gaps** and how to close them, and keywords missing from your resume
   - a **cover letter**, **rewritten resume points** and a **recruiter message**, each with **Copy**
4. The job is saved to your tracker on the Job Copilot website, where you can review, revise and approve the drafts.

It uses the same account, profile and resume as the website, and the same API (`backend/`).

## Install it (developer mode)

The plugin isn't on the Chrome Web Store yet, so you load it from the code. This works in Chrome, Edge and Brave.

1. Get the code: on GitHub, click **Code → Download ZIP** and unzip it, or `git clone` the repository.
2. Open **`chrome://extensions`** in Chrome (Edge: `edge://extensions`, Brave: `brave://extensions`).
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and choose the **`extension`** folder inside the project (the folder that contains `manifest.json`).
5. Click the puzzle-piece icon in the toolbar and **pin** Job Copilot so its icon is always visible.

The first time:

1. Click the Job Copilot icon, then **Settings**.
2. Check the **API address** (your `job-copilot-api-….onrender.com` address from Render) and enter your **Website address**. Click **Save**.
3. **Log in** with your Job Copilot account. You need an account and an uploaded resume, both made on the website.

**After code changes:** go to `chrome://extensions` and click the reload icon on the Job Copilot card.

## Which sites it reads

It can read job pages on LinkedIn, Naukri, Indeed, Instahyre, Wellfound, and company career pages hosted on Greenhouse, Lever, Ashby, Workday and SmartRecruiters. It tries, in order:

1. **Text you selected** on the page. Most reliable: select the description, then click *Read this job*.
2. The site's own description box (best effort; sites change their layouts).
3. The biggest "description"-like section on the page.
4. The page's main content.

On any other site, click the Job Copilot icon on that page first (Chrome then allows reading it), or copy the description and paste it into the box.

## Permissions, and why

| Permission | Why |
|---|---|
| `sidePanel` | Shows the panel beside the page |
| `storage` | Remembers your settings and login on this browser |
| `scripting`, `activeTab` | Reads the job description from the page you're on, only when you click *Read this job* |
| `clipboardWrite` | The **Copy** buttons |
| Site access: `*.onrender.com`, `localhost` | Talks to the Job Copilot API |
| Site access: the job sites listed above | Reads job pages there without an extra click |

The plugin sends the job text to your Job Copilot API and nothing else. Your login token stays in this browser's extension storage.

## Files

| File | What it does |
|---|---|
| `manifest.json` | Tells Chrome what the plugin is and what it may do |
| `background.js` | Opens the side panel when you click the icon |
| `sidepanel.html` / `.css` / `.js` | The panel: log in, read a job, analyse, results, settings |
| `extract.js` | Reads the job description from a page |
| `api.js` | Talks to the Job Copilot API (login, analyse with live progress) |
| `config.js` | Default API and website addresses |
| `icons/` | The toolbar icon |

Plain JavaScript, no build step: what's in this folder is exactly what Chrome runs.

## Not done yet

- Publishing on the Chrome Web Store
- Reviewing, revising and approving drafts inside the panel (use the website for now)
- A tailored resume as a downloadable PDF
