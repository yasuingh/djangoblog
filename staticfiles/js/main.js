/* ============================================================
   DjangoBlog — main.js
   ============================================================ */

"use strict";

// ── Theme toggle ────────────────────────────────────────────────
const THEME_KEY = "djangoblog-theme";

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const icon = document.getElementById("themeIcon");
  if (icon) {
    icon.className = theme === "light" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  }
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || "dark";
  applyTheme(saved);

  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "light" ? "dark" : "light";
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }
}

// ── Scroll: nav shadow ──────────────────────────────────────────
function initNavScroll() {
  const nav = document.getElementById("mainNav");
  if (!nav) return;
  window.addEventListener("scroll", () => {
    nav.style.boxShadow = window.scrollY > 10 ? "0 2px 20px rgba(0,0,0,.35)" : "none";
  }, { passive: true });
}

// ── Reading progress bar ────────────────────────────────────────
function initProgressBar() {
  const article = document.querySelector(".post-article");
  if (!article) return;

  const bar = document.createElement("div");
  bar.id = "readProgress";
  bar.style.cssText = `
    position: fixed; top: 0; left: 0; height: 3px; width: 0;
    background: var(--accent); z-index: 9999; transition: width .1s;
    pointer-events: none; border-radius: 0 2px 2px 0;
  `;
  document.body.appendChild(bar);

  window.addEventListener("scroll", () => {
    const rect = article.getBoundingClientRect();
    const total = article.offsetHeight - window.innerHeight;
    const scrolled = -rect.top;
    const pct = Math.min(100, Math.max(0, (scrolled / total) * 100));
    bar.style.width = pct + "%";
  }, { passive: true });
}

// ── TOC active highlight ────────────────────────────────────────
function initTocObserver() {
  const links = document.querySelectorAll("#tocNav a");
  if (!links.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      const id = entry.target.id;
      const link = document.querySelector(`#tocNav a[href="#${id}"]`);
      if (link) {
        link.style.borderLeftColor = entry.isIntersecting ? "var(--accent)" : "transparent";
        link.style.color = entry.isIntersecting ? "var(--accent)" : "";
        link.style.background = entry.isIntersecting ? "var(--bg-3)" : "";
      }
    });
  }, { rootMargin: "-20% 0px -70% 0px" });

  document.querySelectorAll(".post-body h2, .post-body h3").forEach(h => observer.observe(h));
}

// ── Smooth scroll for TOC links ─────────────────────────────────
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener("click", e => {
      const target = document.querySelector(a.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        window.history.replaceState(null, "", a.getAttribute("href"));
      }
    });
  });
}

// ── Comment like (AJAX) ─────────────────────────────────────────
function initCommentLikes() {
  document.querySelectorAll(".comment-like-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.commentId;
      if (!id) return;

      try {
        const res = await fetch(`/ajax/comment/${id}/like/`, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/json",
          },
        });
        const data = await res.json();
        btn.innerHTML = `<i class="bi bi-heart${data.liked ? "-fill" : ""}"></i> ${data.total}`;
        btn.style.color = data.liked ? "var(--danger)" : "";
      } catch (err) {
        console.error("Like failed", err);
      }
    });
  });
}

// ── Auto-dismiss toasts ─────────────────────────────────────────
function initToasts() {
  document.querySelectorAll(".alert-toast").forEach(toast => {
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity .4s";
      setTimeout(() => toast.remove(), 400);
    }, 5000);
  });
}

// ── Lazy load images polyfill ────────────────────────────────────
function initLazyImages() {
  if ("IntersectionObserver" in window) {
    const imgObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute("data-src");
          }
          imgObserver.unobserve(img);
        }
      });
    });
    document.querySelectorAll("img[data-src]").forEach(img => imgObserver.observe(img));
  }
}

// ── Mobile nav close on link click ─────────────────────────────
function initMobileNav() {
  const collapse = document.getElementById("navContent");
  if (!collapse) return;
  document.querySelectorAll("#navContent .nav-link:not(.dropdown-toggle)").forEach(link => {
    link.addEventListener("click", () => {
      if (window.innerWidth < 992) {
        const bsCollapse = bootstrap.Collapse.getInstance(collapse);
        if (bsCollapse) bsCollapse.hide();
      }
    });
  });
}

// ── Search field: keyboard shortcut (/) ─────────────────────────
function initSearchShortcut() {
  document.addEventListener("keydown", e => {
    if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      e.preventDefault();
      const field = document.querySelector(".search-field");
      if (field) field.focus();
    }
  });
}

// ── Cookie helper ────────────────────────────────────────────────
function getCookie(name) {
  const cookie = document.cookie.split(";").find(c => c.trim().startsWith(name + "="));
  return cookie ? cookie.split("=")[1] : "";
}

// ── Boot ────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initNavScroll();
  initProgressBar();
  initTocObserver();
  initSmoothScroll();
  initCommentLikes();
  initToasts();
  initLazyImages();
  initMobileNav();
  initSearchShortcut();
});
