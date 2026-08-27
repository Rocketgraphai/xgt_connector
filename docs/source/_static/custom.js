document.addEventListener("DOMContentLoaded", function () {
  function updateLogo() {
    const theme = document.documentElement.getAttribute("data-theme") || "light";
    const logo = document.querySelector(".navbar-brand img");

    if (logo) {
      logo.src = theme === "dark" ? "_static/logo-dark.svg" : "_static/logo-light.svg";
    }
  }

  // Run once on load
  updateLogo();

  // Listen for theme changes (if user toggles between light/dark)
  const observer = new MutationObserver(updateLogo);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
});
