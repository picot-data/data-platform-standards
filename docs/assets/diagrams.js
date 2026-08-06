/* Interaction layer for hand-drawn SVG "hero" diagrams.
 * Each interactive element in the SVG is a <g class="dp-node" data-href="...">
 * with a <title> child holding the tooltip text. This script:
 *  - shows that <title> text in a custom, instant tooltip (native <title>
 *    tooltips have an annoying browser delay and inconsistent styling)
 *  - navigates to data-href on click, so a diagram can act as a visual index
 *    into the rest of the site
 */
(function () {
  function initDiagram(svg) {
    var tooltip = document.createElement("div");
    tooltip.className = "dp-tooltip";
    document.body.appendChild(tooltip);

    var nodes = svg.querySelectorAll(".dp-node");
    nodes.forEach(function (node) {
      var titleEl = node.querySelector("title");
      var text = titleEl ? titleEl.textContent : "";

      node.addEventListener("mousemove", function (evt) {
        if (!text) return;
        tooltip.textContent = text;
        tooltip.style.left = evt.clientX + 16 + "px";
        tooltip.style.top = evt.clientY + 16 + "px";
        tooltip.classList.add("dp-tooltip-visible");
      });

      node.addEventListener("mouseleave", function () {
        tooltip.classList.remove("dp-tooltip-visible");
      });

      var href = node.getAttribute("data-href");
      if (href) {
        node.addEventListener("click", function () {
          window.location.href = href;
        });
      }
    });
  }

  function init() {
    document.querySelectorAll(".dp-diagram").forEach(initDiagram);
  }

  if (window.document$) {
    // MkDocs Material's instant navigation emits this observable on every
    // page load, including client-side ones — a plain DOMContentLoaded
    // listener would miss diagrams loaded after the first page.
    window.document$.subscribe(init);
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
