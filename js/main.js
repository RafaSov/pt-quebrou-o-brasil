(function () {
  const chapters = document.querySelector("#capitulos");
  const topbar = document.querySelector("#topbar");
  const progress = document.querySelector("#progress");
  const topicsBar = document.querySelector("#topics-bar");
  const topicsList = document.querySelector("#lista-topicos");
  const menu = document.querySelector("#abrir-topicos");
  const closeBtn = document.querySelector("#fechar-topicos");
  const backdrop = document.querySelector("#backdrop");
  const desktop = window.matchMedia("(min-width: 900px)");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  function setLayout() {
    document.body.classList.toggle("is-desktop", desktop.matches);
    document.body.classList.toggle("is-mobile", !desktop.matches);
    if (desktop.matches) setNav(false);
  }
  setLayout();
  desktop.addEventListener("change", function () {
    setLayout();
    document.querySelectorAll(".chart").forEach(function (chart) {
      const id = chart.closest("article").id;
      const chapter = window.SITE.chapters.find(function (item) { return item.id === id; });
      if (chapter) window.drawChart(chart, chapter);
    });
  });

  function setNav(open) {
    document.body.classList.toggle("nav-open", open);
    menu.setAttribute("aria-expanded", String(open));
  }

  menu.addEventListener("click", function () { setNav(true); });
  closeBtn.addEventListener("click", function () {
    setNav(false);
    menu.focus();
  });
  backdrop.addEventListener("click", function () { setNav(false); });

  const side = document.querySelector("#topicos");
  const canHover = window.matchMedia("(hover: hover)");
  let hoverTimer;
  function hoverOpen() {
    if (desktop.matches || !canHover.matches) return;
    clearTimeout(hoverTimer);
    setNav(true);
  }
  function hoverClose() {
    if (desktop.matches || !canHover.matches) return;
    hoverTimer = setTimeout(function () { setNav(false); }, 180);
  }
  menu.addEventListener("mouseenter", hoverOpen);
  menu.addEventListener("mouseleave", hoverClose);
  side.addEventListener("mouseenter", hoverOpen);
  side.addEventListener("mouseleave", hoverClose);
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && document.body.classList.contains("nav-open")) {
      setNav(false);
      menu.focus();
    }
  });

  function fonteLinha(items) {
    const p = document.createElement("p");
    p.className = "fonte-linha";
    p.appendChild(document.createTextNode("Fontes: "));
    items.forEach(function (item, index) {
      const a = document.createElement("a");
      a.href = item.href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = item.label;
      p.appendChild(a);
      if (index < items.length - 1) p.appendChild(document.createTextNode(", "));
    });
    return p;
  }

  function topicLink(chapter, withIndex) {
    const a = document.createElement("a");
    a.href = "#" + chapter.id;
    if (withIndex && chapter.index) {
      const num = document.createElement("span");
      num.textContent = chapter.index;
      a.appendChild(num);
      a.appendChild(document.createTextNode(chapter.nav || chapter.title));
    } else {
      a.textContent = chapter.nav || chapter.title;
    }
    a.addEventListener("click", function () {
      setNav(false);
      markActive(chapter.id);
      const target = document.getElementById(chapter.id);
      if (target) target.classList.add("is-in");
    });
    return a;
  }

  const seen = new Map();
  function remember(items) {
    items.forEach(function (item) {
      if (!seen.has(item.href)) seen.set(item.href, item.label);
    });
  }

  window.SITE.chapters.forEach(function (chapter) {
    remember(chapter.sources);
    topicsBar.appendChild(topicLink(chapter, false));
    topicsList.appendChild(topicLink(chapter, true));

    const article = document.createElement("article");
    article.id = chapter.id;
    article.className = "reveal";

    const kicker = document.createElement("p");
    kicker.className = "kicker";
    kicker.textContent = chapter.index;
    article.appendChild(kicker);

    const title = document.createElement("h2");
    title.textContent = chapter.title;
    article.appendChild(title);

    chapter.leitura.forEach(function (paragraph) {
      const p = document.createElement("p");
      p.className = "leitura";
      p.textContent = paragraph;
      article.appendChild(p);
    });

    if (chapter.hint) {
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.textContent = chapter.hint;
      article.appendChild(hint);
    }

    if (chapter.series && chapter.series.length) {
      const chart = document.createElement("div");
      chart.className = "chart";
      const head = document.createElement("div");
      head.className = "chart-head";
      const legend = document.createElement("p");
      legend.className = "chart-legend";
      legend.textContent = chapter.series.map(function (serie) { return serie.name; }).join("  ·  ")
        + "  ·  " + chapter.unit;
      const readout = document.createElement("p");
      readout.className = "readout";
      head.append(legend, readout);
      const slot = document.createElement("div");
      slot.className = "chart-svg";
      chart.append(head, slot);
      article.appendChild(chart);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "toggle";
      button.textContent = "Ver números";
      button.setAttribute("aria-expanded", "false");

      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      wrap.hidden = true;
      const table = document.createElement("table");
      const caption = document.createElement("caption");
      caption.textContent = chapter.title + ", em " + chapter.unit;
      table.appendChild(caption);
      const thead = document.createElement("thead");
      const headRow = document.createElement("tr");
      ["Ano"].concat(chapter.series.map(function (serie) { return serie.name; })).forEach(function (label) {
        const th = document.createElement("th");
        th.scope = "col";
        th.textContent = label;
        headRow.appendChild(th);
      });
      thead.appendChild(headRow);
      table.appendChild(thead);
      const tbody = document.createElement("tbody");
      const years = Array.from(new Set(chapter.series.flatMap(function (serie) {
        return serie.points.map(function (point) { return point.year; });
      }))).sort(function (a, b) { return a - b; });
      years.forEach(function (year) {
        const tr = document.createElement("tr");
        const th = document.createElement("th");
        th.scope = "row";
        th.textContent = String(year);
        tr.appendChild(th);
        chapter.series.forEach(function (serie) {
          const td = document.createElement("td");
          const point = serie.points.find(function (item) { return item.year === year; });
          td.textContent = point ? point.value.toLocaleString("pt-BR", {
            minimumFractionDigits: chapter.digits,
            maximumFractionDigits: chapter.digits,
          }) : "—";
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      wrap.appendChild(table);
      button.addEventListener("click", function () {
        const open = wrap.hidden;
        wrap.hidden = !open;
        button.setAttribute("aria-expanded", String(open));
        button.textContent = open ? "Esconder números" : "Ver números";
      });
      article.append(button, wrap);

      const observer = new ResizeObserver(function () { window.drawChart(chart, chapter); });
      observer.observe(chart);
    }

    article.appendChild(fonteLinha(chapter.sources));
    chapters.appendChild(article);
  });

  const fontesTopic = { id: "fontes", nav: "Fontes" };
  topicsBar.appendChild(topicLink(fontesTopic, false));
  topicsList.appendChild(topicLink(fontesTopic, false));

  const fontes = document.querySelector("#lista-fontes");
  seen.forEach(function (label, href) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = label;
    li.appendChild(a);
    fontes.appendChild(li);
  });

  const articleNodes = Array.from(document.querySelectorAll("article, #fontes"));
  const allTopicLinks = Array.from(document.querySelectorAll(".topics a, .side a"));
  const hero = document.querySelector(".hero");

  function markActive(id) {
    allTopicLinks.forEach(function (link) {
      link.classList.toggle("is-active", link.getAttribute("href") === "#" + id);
    });
  }

  function updateSpy() {
    const line = 180;
    let current = articleNodes[0];
    articleNodes.forEach(function (node) {
      if (node.getBoundingClientRect().top <= line) current = node;
    });
    if (current) markActive(current.id);
  }

  const reveals = document.querySelectorAll(".reveal");
  if (reduce.matches) {
    reveals.forEach(function (node) { node.classList.add("is-in"); });
  } else {
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.12 });
    reveals.forEach(function (node) { io.observe(node); });
  }

  function onScroll() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? window.scrollY / max : 0;
    progress.style.width = (ratio * 100) + "%";
    const heroGone = window.scrollY > window.innerHeight * 0.45;
    if (desktop.matches) {
      topbar.classList.toggle("is-on", heroGone);
      topbar.classList.toggle("is-solid", heroGone);
    } else {
      topbar.classList.add("is-on");
      topbar.classList.toggle("is-solid", window.scrollY > 8);
    }
    updateSpy();
  }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("hashchange", onScroll);

  if (hero) {
    const heroWatch = new IntersectionObserver(function (entries) {
      const visible = entries[0] && entries[0].intersectionRatio > 0.35;
      if (desktop.matches) {
        topbar.classList.toggle("is-on", !visible);
        topbar.classList.toggle("is-solid", !visible);
      }
    }, { threshold: [0, 0.2, 0.35, 0.6, 1] });
    heroWatch.observe(hero);
  }
})();
