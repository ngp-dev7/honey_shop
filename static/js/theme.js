(function () {
  "use strict";

  var KEY = "theme";
  var root = document.documentElement;
  var ORDER = [null, "light", "dark"]; // automatic -> light -> dark

  function readChoice() {
    try {
      var value = localStorage.getItem(KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch (error) {
      return null;
    }
  }

  function saveChoice(choice) {
    try {
      if (choice) {
        localStorage.setItem(KEY, choice);
      } else {
        localStorage.removeItem(KEY);
      }
    } catch (error) {
      /* Storage can be blocked; the choice then lasts for this page only. */
    }
  }

  function applyChoice(choice) {
    if (choice) {
      root.setAttribute("data-theme", choice);
    } else {
      root.removeAttribute("data-theme");
    }
    root.setAttribute("data-theme-choice", choice || "system");
  }

  function updateButton(button, choice) {
    var label = button.getAttribute("data-label-" + (choice || "system"));
    if (label) {
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
    }
  }

  // Apply the saved choice at once, before the page is painted.
  var current = readChoice();
  applyChoice(current);

  document.addEventListener("DOMContentLoaded", function () {
    var button = document.querySelector("[data-theme-toggle]");
    if (!button) {
      return;
    }
    button.hidden = false;
    updateButton(button, current);

    button.addEventListener("click", function () {
      current = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];
      saveChoice(current);
      applyChoice(current);
      updateButton(button, current);
    });
  });
})();
