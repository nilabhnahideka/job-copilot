# Job Copilot web app

Next.js 16 (App Router) + Tailwind CSS 4 frontend for the Job Copilot API.

```bash
cp .env.example .env.local   # points at the API, default http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
```

| Route | What it is |
|---|---|
| `/login`, `/signup` | Log in or create an account |
| `/` | Application board, from "To review" through to "Offer" |
| `/profile` | Your profile: resume, personal details, jobs you want, common questions, education, saved answers. Shows what's still missing before applying. |
| `/new` | Paste a job post and watch the agent work step by step (server-sent events) |
| `/applications/[id]` | Fit breakdown, tailored bullets with added words highlighted, cover letter, recruiter message, review and revise |

Every page except log in and sign up needs an account; `<RequireAuth>` sends logged-out visitors to `/login` and back afterwards. The login token is kept in `localStorage` (`lib/auth-token.ts`) and sent as an `Authorization: Bearer` header.

Code map: `lib/api.ts` (typed API client + SSE reader), `components/AuthProvider.tsx` (who is logged in), `components/ProfileView.tsx` + `components/fields.tsx` (profile page and its inputs), `lib/diff.ts` (word-level LCS diff for the bullet highlights), `components/RequirementStrip.tsx` (the fit-score bar), `components/ApplicationView.tsx` (application page).
