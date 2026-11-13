# Deploy guide: put Job Copilot online for free

This puts the app on the internet with three free services. Everything happens in your web browser; no terminal needed. It takes about 20–30 minutes the first time.

| Service | What it does | Free plan notes |
|---|---|---|
| **Neon** | The database: accounts, profiles, applications | No time limit, no card. The database sleeps after 5 minutes idle and wakes in under a second. |
| **Render** | Runs the API and the website | No card. Each service sleeps after 15 minutes without visitors; the next visit takes about a minute to wake it. |
| **Google Gemini** | The AI | Your free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey). |

You need: your Gemini API key, and your GitHub account (the code is already there).

> **Never paste keys or the database address into chats, code, GitHub or screenshots.** They only go into the Neon and Render dashboards.

---

## Part 1: Create the database on Neon (about 5 minutes)

1. Go to **[neon.com](https://neon.com)** and click **Sign up**. Signing up with GitHub or Google is easiest.
2. Create a project:
   - **Project name:** `job-copilot`
   - **Postgres version:** leave the default
   - **Region:** **AWS Asia Pacific (Singapore)**, the closest to India and the same region as the app on Render
   - Click **Create project**.
3. On the project dashboard, click **Connect**. A box shows your **connection string**.
4. In that box, **turn off "Connection pooling"**. The address must *not* contain `-pooler`. (The app keeps its own small set of connections, and LangGraph's checkpoints work best with a direct connection.)
5. Click **Copy**. It looks like this (yours will differ):
   ```
   postgresql://neondb_owner:AbC123...@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
6. Paste it into Notepad for the next part. It contains your database password, so treat it like one.

The app creates all its tables by itself the first time it starts.

---

## Part 2: Create the API and website on Render (about 15 minutes)

1. Go to **[render.com](https://render.com)** and click **Get Started**. **Sign up with GitHub**, so Render can see your repository.
2. In the Render dashboard, click **New +** → **Blueprint**.
3. Connect your **`job-copilot`** repository. (If it isn't listed, click the option to configure GitHub access and allow Render to see `job-copilot`.)
4. Render reads the `render.yaml` file and shows two services, **job-copilot-api** and **job-copilot-web**. Give the Blueprint a name, like `job-copilot`.
5. Render asks for the values that aren't stored in the code. Fill them in:

   | Service | Setting | What to enter |
   |---|---|---|
   | job-copilot-api | `GEMINI_API_KEY` | your Gemini key |
   | job-copilot-api | `DATABASE_URL` | the Neon connection string from Part 1 |
   | job-copilot-api | `CORS_ORIGINS` | `https://job-copilot-web.onrender.com` |
   | job-copilot-web | `NEXT_PUBLIC_API_URL` | `https://job-copilot-api.onrender.com` |

   The last two are the addresses the two services will *probably* get. Step 8 checks them.

6. Click **Apply** (or **Deploy Blueprint**). Render starts building both services. The first build takes about 5–10 minutes.
7. Open **job-copilot-api** → **Logs**. Near the end of the *build* you should see:
   ```
   WORKING: your AI key is set up correctly.
   ```
   If it says `NOT WORKING`, the message after it says why (see Troubleshooting below). The app still deploys; fix the key in **Environment** and redeploy.
8. **Check the two addresses.** At the top of each service's page, Render shows its real address (`https://….onrender.com`).
   - If they are exactly `https://job-copilot-api.onrender.com` and `https://job-copilot-web.onrender.com`, you're done; go to Part 3.
   - If Render added something (for example `https://job-copilot-api-x7k2.onrender.com`, because the name was taken), fix the settings:
     1. **job-copilot-api** → **Environment** → set `CORS_ORIGINS` to the **website's** real address → **Save changes**.
     2. **job-copilot-web** → **Environment** → set `NEXT_PUBLIC_API_URL` to the **API's** real address → **Save changes**.
     3. **job-copilot-web** → **Manual Deploy** → **Deploy latest commit**. The website needs a rebuild because the API address is built into it.

---

## Part 3: Try it

1. Open the website's address (e.g. `https://job-copilot-web.onrender.com`). If it was asleep, the first load takes about a minute.
2. Click **Sign up**, create your account, and fill in your profile.
3. Click **Analyse a job** and paste a job description.

The first request after a quiet period is slow because both the API and the website wake up. That's the free plan, not a bug.

**Updates are automatic:** every time new code is pushed to GitHub's `main` branch, Render rebuilds and redeploys both services.

---

## Things to know about running it publicly

- **Anyone with the link can sign up**, and every analysis they run uses *your* Gemini free-tier quota. Only share the link with people you trust. (Restricting sign-ups to an invite list is a small change if you want it.)
- **Privacy:** on Gemini's free tier, Google may use what's sent to it (resumes, job posts) to improve its products. See [decision 15](decisions.md).
- **Free Render limits:** 750 free hours a month across your services; sleeping services don't use hours. Render may restart free services at any time; your data is safe because it's in Neon.
- **Neon limits:** 0.5–1 GB of storage and 100 compute-hours a month per project; plenty for personal use.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| Build log: `NOT WORKING: ... API key not valid` | Re-copy the Gemini key into `GEMINI_API_KEY` (no spaces or quotes), save, then **Manual Deploy**. |
| Build log: `NOT WORKING: ... not found` (the model) | Set `GEMINI_MODEL` to a model marked "Free of charge" on [Google's pricing page](https://ai.google.dev/gemini-api/docs/pricing), save, redeploy. |
| API log: `Unsafe production settings: ...` | A required setting is missing. The message lists which; add it under **Environment**. |
| API log mentions `connection` or `password authentication failed` | `DATABASE_URL` is wrong. Copy it again from Neon (pooling off) and save. |
| Website says "Can't reach the API" | `NEXT_PUBLIC_API_URL` is wrong or the API is still waking. Wait a minute and reload. If it persists, fix the address (Part 2, step 8) and redeploy the website. |
| Browser console shows a "CORS" error | `CORS_ORIGINS` on the API doesn't match the website's address exactly. Fix it (Part 2, step 8). No rebuild of the website needed. |
| Analysing a job fails with "quota" or "429" | Gemini's free per-minute limit. Wait a minute and try again. |
