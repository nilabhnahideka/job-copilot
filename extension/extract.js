// Reads the job description from the page you're looking at.
//
// `extractJobFromPage` is injected INTO the job page by chrome.scripting, so it
// must be completely self-contained: no imports, no outside variables.
// It tries, in order:
//   1. Text you've selected on the page (the most reliable: you choose exactly what to send)
//   2. Known description boxes on popular job sites (these change often; that's why there are fallbacks)
//   3. The largest block whose class/id looks like "description" / "job details"
//   4. The page's <main> or <article>, then the whole page
// The side panel shows the result in a text box, so you can always fix it before analysing.

export function extractJobFromPage() {
  const MAX_CHARS = 15000; // the API accepts up to 50,000; long pages are mostly noise
  const MIN_CHARS = 200; // less than this is probably not a job description

  const clean = (t) =>
    (t || "")
      .replace(/ /g, " ")
      .replace(/[ \t]+/g, " ")
      .replace(/\n\s*\n\s*\n+/g, "\n\n")
      .trim();
  const textOf = (el) => clean(el && (el.innerText || el.textContent));
  const result = (text, source) => ({
    url: location.href,
    pageTitle: document.title,
    text: text.slice(0, MAX_CHARS),
    truncated: text.length > MAX_CHARS,
    source,
  });

  // 1. The user's own selection
  const selected = clean(window.getSelection && window.getSelection().toString());
  if (selected.length >= 50) return result(selected, "your selection");

  // 2. Known job sites. Selectors are best-effort and may break when sites change.
  const host = location.hostname;
  const SITE_SELECTORS = [
    [/linkedin\.com$/, ["#job-details", ".jobs-description__content", ".jobs-description-content__text", ".jobs-box__html-content"]],
    [/naukri\.com$/, ["[class*='job-desc']", "[class*='JDC']", "section[class*='job-desc']"]],
    [/indeed\.com$/, ["#jobDescriptionText", "[data-testid='jobsearch-JobComponent-description']"]],
    [/greenhouse\.io$/, ["#content", ".job__description", "[class*='job-post']"]],
    [/lever\.co$/, [".posting-page .content", ".section-wrapper.page-full-width"]],
    [/ashbyhq\.com$/, ["[class*='descriptionText']", "[class*='_description']"]],
    [/myworkdayjobs\.com$/, ["[data-automation-id='jobPostingDescription']"]],
    [/smartrecruiters\.com$/, ["[itemprop='description']", ".job-sections"]],
    [/instahyre\.com$/, ["[class*='job-description']"]],
    [/wellfound\.com$/, ["[class*='description']"]],
  ];
  for (const [pattern, selectors] of SITE_SELECTORS) {
    if (!pattern.test(host)) continue;
    for (const sel of selectors) {
      const t = textOf(document.querySelector(sel));
      if (t.length >= MIN_CHARS) {
        // Put the job title on top when we can find it, it helps the AI.
        const title = textOf(document.querySelector("h1"));
        return result(title && !t.startsWith(title) ? `${title}\n\n${t}` : t, "this job site's description box");
      }
    }
  }

  // 3. The biggest description-like block on any site
  const candidates = document.querySelectorAll(
    "[class*='description' i], [id*='description' i], [class*='job-details' i], [id*='job-details' i], [class*='jobdetails' i], [itemprop='description']",
  );
  let best = "";
  for (const el of candidates) {
    const t = textOf(el);
    if (t.length > best.length) best = t;
  }
  if (best.length >= MIN_CHARS) {
    const title = textOf(document.querySelector("h1"));
    return result(title && !best.startsWith(title) ? `${title}\n\n${best}` : best, "the page's description section");
  }

  // 4. Main content, then everything
  const main = textOf(document.querySelector("main") || document.querySelector("article"));
  if (main.length >= MIN_CHARS) return result(main, "the page's main content");
  return result(textOf(document.body), "the whole page");
}
