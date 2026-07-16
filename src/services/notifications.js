(function initializeCodeNotifications(global) {
  "use strict";

  const services = global.Code && global.Code.services;
  if (!services) {
    throw new Error("Code services namespace must load before notifications");
  }

  function showToast(message, type = "error") {
    const container = global.document.getElementById("toastContainer");
    if (!container) return;

    const toast = global.document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    global.setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity .2s";
      global.setTimeout(() => toast.remove(), 200);
    }, 3000);
  }

  function notify(title, body) {
    try {
      if ("Notification" in global && global.Notification.permission === "granted") {
        return new global.Notification(title, { body, icon: "code-icon.png" });
      }
    } catch (_) {}
    return null;
  }

  services.notifications = Object.freeze({
    showToast,
    notify,
  });
})(window);
