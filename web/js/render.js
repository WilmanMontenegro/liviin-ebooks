function el(tag, cls, html) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

function renderCover(page, book) {
  const root = el("article", "page cover");
  root.id = page.id;
  const img = document.createElement("img");
  img.className = "cover-img";
  img.src = book.coverImage || page.image || "";
  img.alt = "";
  root.appendChild(img);
  root.appendChild(el("div", "cover-fade"));
  const text = el("div", "cover-text");
  text.appendChild(el("div", "series", page.series || book.series));
  text.appendChild(el("h2", "cover-title", page.title || book.title));
  if (page.subtitle) text.appendChild(el("p", "cover-sub", page.subtitle));
  root.appendChild(text);
  const logo = (page.logo || "liviin").split("\n");
  root.appendChild(
    el("div", "cover-logo", `${logo[0]}<small>${logo[1] || "for better living"}</small>`)
  );
  return root;
}

function renderContent(page) {
  const hasFooter = !!page.footer;
  const root = el("article", `page${hasFooter ? "" : " no-footer"}`);
  root.id = page.id;
  const inner = el("div", "page-inner");
  if (page.label) inner.appendChild(el("p", "page-label", page.label));
  if (page.title) inner.appendChild(el("h2", "page-title", page.title));
  if (page.subtitle) inner.appendChild(el("p", "page-subtitle", page.subtitle));
  if (page.title) inner.appendChild(el("hr", "title-rule"));
  const body = el("div", "page-body");
  for (const p of page.paragraphs || []) {
    body.appendChild(el("p", null, p));
  }
  for (const item of page.list || []) {
    const wrap = el("div", "list-item");
    wrap.appendChild(el("div", "li-label", item.label));
    wrap.appendChild(el("p", null, item.text));
    body.appendChild(wrap);
  }
  inner.appendChild(body);
  root.appendChild(inner);
  if (hasFooter) {
    const foot = el("footer", "page-footer");
    foot.appendChild(el("span", null, page.footer.section));
    foot.appendChild(el("span", "num", String(page.footer.number)));
    root.appendChild(foot);
  }
  return root;
}

function renderQuote(page) {
  const root = el("article", "page quote no-footer");
  root.id = page.id;
  const inner = el("div", "page-inner");
  inner.appendChild(el("blockquote", null, page.text));
  inner.appendChild(el("cite", null, page.cite));
  root.appendChild(inner);
  return root;
}

function renderOpener(page) {
  const root = el("article", "page opener no-footer");
  root.id = page.id;
  const inner = el("div", "page-inner");
  if (page.label) inner.appendChild(el("p", "page-label", page.label));
  inner.appendChild(el("h2", "page-title", page.title));
  if (page.subtitle) inner.appendChild(el("p", "page-subtitle", page.subtitle));
  root.appendChild(inner);
  return root;
}

function renderPage(page, book) {
  switch (page.type) {
    case "cover":
      return renderCover(page, book);
    case "quote":
      return renderQuote(page);
    case "opener":
      return renderOpener(page);
  }
  return renderContent(page);
}

async function boot() {
  const params = new URLSearchParams(location.search);
  const src = params.get("book") || "content/transformar-pilot.json";
  const res = await fetch(src);
  const data = await res.json();
  const nav = document.getElementById("nav-links");
  const main = document.getElementById("pages");
  document.getElementById("book-title").textContent = data.book.title;
  document.getElementById("book-meta").textContent =
    `Piloto · ${data.pages.length} páginas · plantilla Liderar`;

  for (const page of data.pages) {
    const node = renderPage(page, data.book);
    main.appendChild(node);
    const a = document.createElement("a");
    a.href = `#${page.id}`;
    a.textContent = `${page.id} · ${page.type}`;
    nav.appendChild(a);
  }
}

boot().catch((err) => {
  document.body.innerHTML = `<pre style="color:#f88;padding:2rem">${err}</pre>`;
});
