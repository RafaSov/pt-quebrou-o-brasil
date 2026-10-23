(function () {
  const MARKS = [
    { year: 2003, label: "2003" },
    { year: 2023, label: "2023" },
  ];

  function format(value, digits) {
    return value.toLocaleString("pt-BR", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function segments(points) {
    const sorted = points.slice().sort(function (a, b) { return a.year - b.year; });
    const groups = [];
    let current = [];
    sorted.forEach(function (point) {
      if (current.length && point.year !== current[current.length - 1].year + 1) {
        groups.push(current);
        current = [];
      }
      current.push(point);
    });
    if (current.length) groups.push(current);
    return groups;
  }

  function draw(host, chapter) {
    const mobile = window.innerWidth < 900;
    const width = Math.max(Math.round(host.clientWidth), 280);
    const height = mobile ? 280 : 400;
    const pad = mobile
      ? { l: 46, r: 10, t: 26, b: 32 }
      : { l: 64, r: 18, t: 32, b: 40 };
    const plotW = width - pad.l - pad.r;
    const plotH = height - pad.t - pad.b;
    const all = chapter.series.flatMap(function (serie) { return serie.points; });
    const years = all.map(function (point) { return point.year; });
    const values = all.map(function (point) { return point.value; });
    const minYear = Math.min.apply(null, years);
    const maxYear = Math.max.apply(null, years);
    let minVal = Math.min.apply(null, values);
    let maxVal = Math.max.apply(null, values);
    const span = maxVal - minVal || Math.abs(maxVal) || 1;
    if (chapter.axisZero && minVal > 0) minVal = 0;
    else minVal -= span * 0.14;
    maxVal += span * 0.16;

    const x = function (year) {
      if (maxYear === minYear) return pad.l + plotW / 2;
      return pad.l + ((year - minYear) / (maxYear - minYear)) * plotW;
    };
    const y = function (value) {
      return pad.t + (1 - (value - minVal) / (maxVal - minVal)) * plotH;
    };
    const step = maxYear === minYear ? plotW : plotW / (maxYear - minYear);

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", String(width));
    svg.setAttribute("height", String(height));
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", chapter.title + ". " + chapter.unit + ".");

    function el(name, attrs) {
      const node = document.createElementNS("http://www.w3.org/2000/svg", name);
      Object.keys(attrs).forEach(function (key) { node.setAttribute(key, attrs[key]); });
      return node;
    }

    const ticks = mobile ? 3 : 4;
    for (let i = 0; i <= ticks; i += 1) {
      const value = minVal + ((maxVal - minVal) * i) / ticks;
      const yy = y(value);
      svg.appendChild(el("line", {
        x1: pad.l, x2: width - pad.r, y1: yy, y2: yy,
        stroke: "#2a2a2a", "stroke-width": "1",
      }));
      const label = el("text", { x: pad.l - 8, y: yy + 4, "text-anchor": "end", "font-size": mobile ? "11" : "13" });
      label.textContent = format(value, chapter.digits > 2 ? 2 : chapter.digits);
      svg.appendChild(label);
    }

    if (maxYear > 2016 && minYear < 2022) {
      const x0 = Math.max(pad.l, x(2016) - step / 2);
      const x1 = Math.min(width - pad.r, x(2022) + step / 2);
      svg.appendChild(el("rect", {
        x: x0, y: pad.t, width: Math.max(x1 - x0, 0), height: plotH, fill: "rgba(244,241,234,0.07)",
      }));
    }

    MARKS.forEach(function (mark) {
      if (mark.year < minYear || mark.year > maxYear) return;
      const xx = x(mark.year);
      svg.appendChild(el("line", {
        x1: xx, x2: xx, y1: pad.t, y2: pad.t + plotH,
        stroke: "#e10600", "stroke-width": "1.5",
      }));
      const placeLeft = xx > pad.l + plotW * 0.7;
      const label = el("text", {
        x: placeLeft ? xx - 6 : xx + 6,
        y: 16,
        class: "mark",
        "text-anchor": placeLeft ? "end" : "start",
        "font-size": mobile ? "11" : "13",
      });
      label.textContent = mark.label;
      svg.appendChild(label);
    });

    const colors = ["#f4f1ea", "#7ec8d4"];
    chapter.series.forEach(function (serie, index) {
      const color = colors[index % colors.length];
      segments(serie.points).forEach(function (group) {
        if (group.length === 1) {
          svg.appendChild(el("circle", {
            cx: x(group[0].year), cy: y(group[0].value), r: "3.5", fill: color,
          }));
          return;
        }
        const d = group.map(function (point, i) {
          return (i === 0 ? "M" : "L") + x(point.year) + " " + y(point.value);
        }).join(" ");
        const path = el("path", {
          d: d, fill: "none", stroke: color, "stroke-width": mobile ? "2.2" : "2.6",
          "stroke-linejoin": "round", "stroke-linecap": "round",
          class: "draw",
          "pathLength": "1",
        });
        svg.appendChild(path);
      });
    });

    const tickYears = [minYear, maxYear];
    [1995, 2000, 2003, 2010, 2016, 2023, 2025].forEach(function (year) {
      if (year > minYear && year < maxYear) tickYears.push(year);
    });
    tickYears.sort(function (a, b) { return a - b; });
    let lastX = -Infinity;
    const minGap = mobile ? 44 : 36;
    tickYears.forEach(function (year) {
      const xx = x(year);
      if (xx - lastX < minGap) return;
      lastX = xx;
      let anchor = "middle";
      let lx = xx;
      if (xx < pad.l + 16) {
        anchor = "start";
        lx = pad.l;
      } else if (xx > width - pad.r - 16) {
        anchor = "end";
        lx = width - pad.r;
      }
      const label = el("text", { x: lx, y: height - 10, "text-anchor": anchor, "font-size": mobile ? "11" : "13" });
      label.textContent = String(year);
      svg.appendChild(label);
    });

    const flat = [];
    chapter.series.forEach(function (serie) {
      serie.points.forEach(function (point) {
        flat.push({ year: point.year, value: point.value, name: serie.name });
      });
    });

    const guide = el("line", {
      x1: pad.l, x2: pad.l, y1: pad.t, y2: pad.t + plotH,
      stroke: "rgba(244,241,234,0.28)", "stroke-width": "1",
      "stroke-dasharray": "3 4",
    });
    guide.style.display = "none";
    svg.appendChild(guide);

    const dots = chapter.series.map(function (serie, index) {
      const dot = el("circle", {
        cx: "0", cy: "0", r: "4.5",
        fill: colors[index % colors.length],
        stroke: "#070707",
        "stroke-width": "2",
      });
      dot.style.display = "none";
      svg.appendChild(dot);
      return dot;
    });

    const readout = host.querySelector(".readout");
    const idle = mobile ? "Toque a linha para ver o ano" : "Passe o cursor sobre a linha";

    function show(event) {
      const rect = svg.getBoundingClientRect();
      const px = ((event.clientX - rect.left) / rect.width) * width;
      let nearest = flat[0];
      let best = Infinity;
      flat.forEach(function (point) {
        const dist = Math.abs(x(point.year) - px);
        if (dist < best) {
          best = dist;
          nearest = point;
        }
      });
      const sameYear = flat.filter(function (point) { return point.year === nearest.year; });
      readout.textContent = sameYear.map(function (point) {
        const name = chapter.series.length > 1 ? point.name + ": " : "";
        return nearest.year + " · " + name + format(point.value, chapter.digits) + " " + chapter.unit;
      }).join("   ");
      const gx = x(nearest.year);
      guide.setAttribute("x1", String(gx));
      guide.setAttribute("x2", String(gx));
      guide.style.display = "";
      chapter.series.forEach(function (serie, index) {
        const point = serie.points.find(function (item) { return item.year === nearest.year; });
        if (!point) {
          dots[index].style.display = "none";
          return;
        }
        dots[index].setAttribute("cx", String(x(point.year)));
        dots[index].setAttribute("cy", String(y(point.value)));
        dots[index].style.display = "";
      });
    }

    function hide() {
      readout.textContent = idle;
      guide.style.display = "none";
      dots.forEach(function (dot) { dot.style.display = "none"; });
    }

    svg.addEventListener("pointermove", show);
    svg.addEventListener("pointerleave", hide);
    readout.textContent = idle;

    const slot = host.querySelector(".chart-svg");
    slot.replaceChildren(svg);
  }

  window.drawChart = draw;
})();
