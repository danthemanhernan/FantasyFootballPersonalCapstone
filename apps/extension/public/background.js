chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ fantasyHudInstalledAt: new Date().toISOString() });
});
