const downloadLinks = document.querySelectorAll('.btn-download-trigger');
  const toast = document.getElementById('download-toast');
  let toastTimeout;

  downloadLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      // Don't prevent default, let the download happen
      showToast();
    });
  });

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