/* Interaction layer for the SVG "hero" diagrams (docs/assets/diagrams/*.svg).
 *
 * Each interactive element is a <g class="dp-node"> holding a <title> with the
 * tooltip text and, optionally, a data-href pointing at the page or section
 * that explains it. This script:
 *
 *  - shows the <title> text in a custom, instant tooltip and *removes* the
 *    <title> element. Leaving it in the DOM makes the browser draw its own
 *    native tooltip about a second later, on top of ours;
 *  - resolves data-href, which is written as a source path
 *    ("data-layers.md#the-two-axes"), into a real site URL. MkDocs only
 *    rewrites .md links it finds in markdown, and these live inside a raw SVG
 *    block, so untouched they would 404;
 *  - adds an "enlarge" control, because these diagrams carry more detail than
 *    fits in the content column.
 */
(function () {
  var ESC = 27;

  /* ---------------------------------------------------------------- URLs */

  // Material publishes the site's base URL (relative to the current page) in
  // its config blob — the only reliable way to build a link from a raw SVG.
  function siteBase() {
    var el = document.getElementById("__config");
    if (!el) return ".";
    try {
      return JSON.parse(el.textContent).base || ".";
    } catch (err) {
      return ".";
    }
  }

  function resolveHref(href, base) {
    if (!href) return null;
    // Absolute URL (http:, https:, mailto:) or protocol-relative: leave alone.
    if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.indexOf("//") === 0) {
      return href;
    }
    if (href.charAt(0) === "#") return href;

    var hash = "";
    var cut = href.indexOf("#");
    if (cut !== -1) {
      hash = href.slice(cut);
      href = href.slice(0, cut);
    }
    var page = href.replace(/\.md$/, "");
    if (page === "index") page = "";
    return base.replace(/\/$/, "") + "/" + (page ? page + "/" : "") + hash;
  }

  /* ------------------------------------------------------------- tooltip */

  // One tooltip for the whole document, reused across diagrams and across
  // instant-navigation page loads (which leave <body> children in place).
  function tooltip() {
    var el = document.querySelector(".dp-tooltip");
    if (!el) {
      el = document.createElement("div");
      el.className = "dp-tooltip";
      el.setAttribute("role", "tooltip");
      document.body.appendChild(el);
    }
    return el;
  }

  function showTooltip(text, x, y) {
    var tip = tooltip();
    tip.textContent = text;
    tip.classList.add("dp-tooltip-visible");

    // Measure only once visible, then keep the box inside the viewport —
    // nodes near the right or bottom edge would otherwise push it off-screen.
    var box = tip.getBoundingClientRect();
    var left = Math.min(x + 16, window.innerWidth - box.width - 12);
    var top = y + 18;
    if (top + box.height > window.innerHeight - 12) {
      top = y - box.height - 14;
    }
    tip.style.left = Math.max(12, left) + "px";
    tip.style.top = Math.max(12, top) + "px";
  }

  function hideTooltip() {
    var tip = document.querySelector(".dp-tooltip");
    if (tip) tip.classList.remove("dp-tooltip-visible");
  }

  /* ------------------------------------------------------------- overlay */

  var open = null; // { svg: SVGElement, anchor: Comment }

  function overlay() {
    var el = document.querySelector(".dp-overlay");
    if (el) return el;

    el = document.createElement("div");
    el.className = "dp-overlay";
    el.innerHTML =
      '<div class="dp-stage"></div>' +
      '<button class="dp-overlay-close" type="button" ' +
      'aria-label="Close the enlarged diagram">&times;</button>';
    el.addEventListener("click", function (evt) {
      // Only the backdrop and the close button close the overlay; clicks
      // inside the diagram itself still navigate.
      if (evt.target === el || evt.target.className === "dp-overlay-close") {
        closeOverlay();
      }
    });
    document.body.appendChild(el);
    return el;
  }

  function openOverlay(svg) {
    if (open) closeOverlay();

    // Move the live <svg> rather than cloning it, so the node listeners
    // registered below keep working in the enlarged view.
    var anchor = document.createComment("dp-diagram");
    svg.parentNode.insertBefore(anchor, svg);

    var el = overlay();
    el.querySelector(".dp-stage").appendChild(svg);
    svg.classList.add("dp-diagram-full");
    el.classList.add("dp-overlay-visible");
    document.body.classList.add("dp-overlay-open");
    el.querySelector(".dp-overlay-close").focus();

    open = { svg: svg, anchor: anchor };
  }

  function closeOverlay() {
    if (!open) return;
    open.svg.classList.remove("dp-diagram-full");
    open.anchor.parentNode.replaceChild(open.svg, open.anchor);

    var el = document.querySelector(".dp-overlay");
    if (el) el.classList.remove("dp-overlay-visible");
    document.body.classList.remove("dp-overlay-open");
    hideTooltip();
    open = null;
  }

  document.addEventListener("keydown", function (evt) {
    if ((evt.keyCode === ESC || evt.key === "Escape") && open) closeOverlay();
  });

  /* ---------------------------------------------------------------- init */

  function initNode(node, base) {
    var titleEl = node.querySelector("title");
    var text = "";
    if (titleEl) {
      text = titleEl.textContent;
      // See the header comment: this is what kills the duplicate tooltip.
      titleEl.parentNode.removeChild(titleEl);
    }

    if (text) {
      node.addEventListener("mousemove", function (evt) {
        showTooltip(text, evt.clientX, evt.clientY);
      });
      node.addEventListener("mouseleave", hideTooltip);
    }

    var href = resolveHref(node.getAttribute("data-href"), base);
    if (!href) return;

    node.setAttribute("role", "link");
    node.setAttribute("tabindex", "0");
    if (text) node.setAttribute("aria-label", text);

    function go() {
      closeOverlay();
      window.location.href = href;
    }
    node.addEventListener("click", go);
    node.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        go();
      }
    });
    node.addEventListener("focus", function () {
      var box = node.getBoundingClientRect();
      if (text) showTooltip(text, box.left, box.bottom - 18);
    });
    node.addEventListener("blur", hideTooltip);
  }

  function initDiagram(svg) {
    if (svg.dataset.dpReady) return;
    svg.dataset.dpReady = "1";

    var base = siteBase();
    Array.prototype.forEach.call(svg.querySelectorAll(".dp-node"), function (n) {
      initNode(n, base);
    });

    var wrap = svg.closest(".dp-diagram-wrap");
    if (!wrap || wrap.querySelector(".dp-enlarge")) return;

    var button = document.createElement("button");
    button.type = "button";
    button.className = "dp-enlarge";
    button.textContent = "Enlarge";
    button.setAttribute("aria-label", "Enlarge this diagram");
    button.addEventListener("click", function () {
      openOverlay(svg);
    });
    wrap.appendChild(button);
  }

  function init() {
    closeOverlay();
    Array.prototype.forEach.call(
      document.querySelectorAll(".dp-diagram"),
      initDiagram
    );
  }

  if (window.document$) {
    // MkDocs Material's instant navigation emits this observable on every page
    // load, including client-side ones — a plain DOMContentLoaded listener
    // would miss diagrams on every page after the first.
    window.document$.subscribe(init);
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
