// Background script: runs in the background, not on any page.
// Its only job: open the side panel when you click the Job Copilot icon.

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((err) => console.error(err));
});
