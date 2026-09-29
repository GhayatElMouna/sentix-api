const $ = (id) => document.getElementById(id);

const LABELS = {
  positive: "Positif",
  negative: "Négatif",
  neutral: "Neutre",
};

$("analyze").addEventListener("click", analyze);
$("post-url").addEventListener("change", loadPost);
$("post-url").addEventListener("blur", loadPost);

function setBanner(message) {
  const el = $("banner");
  el.hidden = !message;
  el.textContent = message || "";
}

function setStatus(message) {
  const el = $("status");
  el.hidden = !message;
  el.textContent = message || "";
}

function errorMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item).join(" ");
  }
  return "Analyse impossible.";
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function parseResponse(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(errorMessage(data.detail));
  }
  return data;
}

async function loadPost() {
  const url = $("post-url").value.trim();
  $("latest").innerHTML = "";
  if (!url) {
    $("counters").innerHTML = "";
    $("history").innerHTML = "";
    return;
  }

  try {
    const response = await fetch(`/posts?url=${encodeURIComponent(url)}`);
    const post = await parseResponse(response);
    renderPost(post, { keepLatest: false });
  } catch (err) {
    setBanner(err.message);
  }
}

async function analyze() {
  const url = $("post-url").value.trim();
  const text = $("comment").value.trim();
  setBanner("");
  setStatus("");

  if (!url) {
    setBanner("Indiquez le lien du post avant d’analyser.");
    $("post-url").focus();
    return;
  }
  if (!text) {
    setBanner("Saisissez un commentaire à analyser.");
    $("comment").focus();
    return;
  }

  const button = $("analyze");
  button.disabled = true;
  button.textContent = "Analyse en cours…";
  setStatus("Analyse du commentaire…");

  try {
    const response = await fetch("/posts/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, text }),
    });
    const data = await parseResponse(response);
    setStatus("");
    renderLatest(data.result, data.duplicate);
    renderPost(data.post, { keepLatest: true });
    $("comment").value = "";
  } catch (err) {
    setStatus("");
    setBanner(err.message || "Une erreur est survenue.");
  } finally {
    button.disabled = false;
    button.textContent = "Lancer l’analyse";
  }
}

function renderLatest(result, duplicate) {
  const sentiment = result.sentiment;
  $("latest").innerHTML = `
    <section class="latest">
      <p class="latest-label">Analyse du commentaire</p>
      <p class="latest-text">${escapeHtml(result.text)}</p>
      <span class="verdict ${sentiment}">${LABELS[sentiment] || sentiment}</span>
      ${
        duplicate
          ? `<p class="note">Ce commentaire a déjà été compté pour ce post. Les totaux n’ont pas changé.</p>`
          : ""
      }
    </section>
  `;
}

function renderPost(post, { keepLatest = false } = {}) {
  if (!keepLatest) {
    $("latest").innerHTML = "";
  }

  if (!post.exists || !post.total) {
    $("counters").innerHTML = "";
    $("history").innerHTML = "";
    return;
  }

  $("counters").innerHTML = `
    <section class="counters" aria-label="Compteurs du post">
      <article class="counter positive">
        <span>Positive</span>
        <strong>${post.positiveCount}</strong>
      </article>
      <article class="counter negative">
        <span>Negative</span>
        <strong>${post.negativeCount}</strong>
      </article>
      <article class="counter">
        <span>Total</span>
        <strong>${post.total}</strong>
      </article>
    </section>
  `;

  const items = [...post.comments].reverse();
  $("history").innerHTML = `
    <section class="history">
      <h2>Détail des analyses</h2>
      <ul class="history-list">
        ${items
          .map(
            (item) => `
          <li>
            <span class="badge ${item.sentiment}">${LABELS[item.sentiment] || item.sentiment}</span>
            <p>${escapeHtml(item.text)}</p>
          </li>`
          )
          .join("")}
      </ul>
    </section>
  `;
}
