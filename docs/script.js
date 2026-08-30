const downloadLinks = document.querySelectorAll('.btn-download-trigger');
const toast = document.getElementById('download-toast');
let toastTimeout;

const ASSET_NAME = 'Setup_Windows_x64.exe';
const RELEASES_API = 'https://api.github.com/repos/RandomCatUser/SweetVibe/releases/latest';
const RELEASES_PAGE = 'https://github.com/RandomCatUser/SweetVibe/releases/latest';

// Resolve the most recent installer download URL once, then update all
// download buttons so they never point to a stale or missing version.
async function resolveLatestDownload() {
  try {
    const res = await fetch(RELEASES_API, { headers: { Accept: 'application/vnd.github+json' } });
    if (!res.ok) throw new Error('bad status');
    const release = await res.json();
    const asset = (release.assets || []).find((a) => a.name === ASSET_NAME);
    if (asset && asset.browser_download_url) return asset.browser_download_url;
  } catch (e) {
    // fall through to the releases page
  }
  return RELEASES_PAGE;
}

async function wireDownloadButtons() {
  const latestUrl = await resolveLatestDownload();
  downloadLinks.forEach((link) => {
    link.setAttribute('href', latestUrl);
    link.addEventListener('click', () => showToast());
  });
}

function showToast() {
  clearTimeout(toastTimeout);
  toast.classList.add('show');
  // Auto-hide after 5 seconds
  toastTimeout = setTimeout(() => {
    toast.classList.remove('show');
  }, 5000);
}

function hideToast() {
  clearTimeout(toastTimeout);
  toast.classList.remove('show');
}

wireDownloadButtons();
