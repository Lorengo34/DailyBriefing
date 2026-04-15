import feedparser
import anthropic
import os
from datetime import datetime

# ── Configurazione feed RSS ──────────────────────────────────────────────────
RSS_FEEDS = {
    "ANSA":         "https://www.ansa.it/sito/ansait_rss.xml",
    "Sky TG24":     "https://tg24.sky.it/rss/cronaca.xml",
    "Il Sole 24 Ore": "https://www.ilsole24ore.com/rss/mondo.xml",
}

MAX_ITEMS_PER_FEED = 15   # quante notizie leggere per fonte


def fetch_news() -> list[dict]:
    """Legge tutti i feed RSS e restituisce una lista di notizie {source, title, summary}."""
    news = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # Rimuove tag HTML semplici dal sommario
                import re
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                summary = re.sub(r"\s{2,}", " ", summary)
                if title:
                    news.append({"source": source, "title": title, "summary": summary[:300]})
            print(f"  ✓ {source}: {len(feed.entries[:MAX_ITEMS_PER_FEED])} notizie")
        except Exception as e:
            print(f"  ✗ Errore leggendo {source}: {e}")
    return news


def build_briefing(news: list[dict]) -> str:
    """Invia le notizie a Claude e ottiene il briefing sintetizzato."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Formatta le notizie come testo da passare al modello
    news_block = "\n\n".join(
        f"[{item['source']}]\nTitolo: {item['title']}\nSommario: {item['summary']}"
        for item in news
    )

    system_prompt = (
        "Sei un giornalista analitico. Crea un briefing delle notizie più importanti di oggi "
        "in circa 600 parole. Usa un tono asciutto, evita il clickbait, raggruppa le notizie "
        "per temi (Politica, Cronaca, Mondo) e scarta i duplicati. "
        "Scrivi in italiano. Non usare markdown, solo testo piano con i titoli delle sezioni "
        "in maiuscolo seguiti da due punti."
    )

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1200,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Ecco le notizie di oggi:\n\n{news_block}"}
        ],
    )
    return message.content[0].text


def render_html(briefing: str) -> str:
    """Genera l'HTML della pagina a partire dal testo del briefing."""
    now       = datetime.utcnow()
    date_it   = now.strftime("%-d %B %Y").replace(
        "January","gennaio").replace("February","febbraio").replace(
        "March","marzo").replace("April","aprile").replace(
        "May","maggio").replace("June","giugno").replace(
        "July","luglio").replace("August","agosto").replace(
        "September","settembre").replace("October","ottobre").replace(
        "November","novembre").replace("December","dicembre")
    time_utc  = now.strftime("%H:%M UTC")

    # Converte il testo in paragrafi HTML
    import html as html_lib
    paragraphs_html = ""
    for line in briefing.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        escaped = html_lib.escape(line)
        # Linee in maiuscolo → heading di sezione
        if line.isupper() or (line.endswith(":") and len(line) < 40 and line == line.upper()):
            paragraphs_html += f'<h2 class="section-title">{escaped}</h2>\n'
        else:
            paragraphs_html += f'<p>{escaped}</p>\n'

    sources_list = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener">{name}</a></li>'
        for name, url in RSS_FEEDS.items()
    )

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Briefing Quotidiano — {date_it}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600&display=swap" rel="stylesheet" />

  <style>
    /* ── Reset & base ─────────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --ink:        #1a1a1a;
      --ink-light:  #555;
      --paper:      #faf8f4;
      --rule:       #ddd8ce;
      --accent:     #c0392b;
      --max-w:      680px;
    }}

    body {{
      background: var(--paper);
      color: var(--ink);
      font-family: 'Source Sans 3', sans-serif;
      font-weight: 300;
      font-size: clamp(16px, 2.2vw, 18px);
      line-height: 1.75;
      padding: 2rem 1.25rem 4rem;
    }}

    /* ── Layout container ─────────────────────────────── */
    .wrapper {{
      max-width: var(--max-w);
      margin: 0 auto;
    }}

    /* ── Masthead ─────────────────────────────────────── */
    header {{
      border-top: 3px solid var(--ink);
      padding-top: 2rem;
      margin-bottom: 2.5rem;
    }}

    .eyebrow {{
      font-family: 'Source Sans 3', sans-serif;
      font-weight: 600;
      font-size: 0.72rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 0.4rem;
    }}

    h1 {{
      font-family: 'Libre Baskerville', Georgia, serif;
      font-size: clamp(2rem, 6vw, 3rem);
      font-weight: 700;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--ink);
    }}

    .dateline {{
      margin-top: 0.6rem;
      font-size: 0.82rem;
      color: var(--ink-light);
      letter-spacing: 0.04em;
    }}

    .rule {{
      border: none;
      border-top: 1px solid var(--rule);
      margin: 2rem 0;
    }}

    /* ── Article body ─────────────────────────────────── */
    .briefing-body h2.section-title {{
      font-family: 'Source Sans 3', sans-serif;
      font-weight: 600;
      font-size: 0.72rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent);
      margin-top: 2.2rem;
      margin-bottom: 0.75rem;
      padding-bottom: 0.4rem;
      border-bottom: 1px solid var(--rule);
    }}

    .briefing-body p {{
      font-family: 'Libre Baskerville', Georgia, serif;
      font-size: 1rem;
      line-height: 1.8;
      margin-bottom: 1.1rem;
      color: var(--ink);
    }}

    /* ── Footer ───────────────────────────────────────── */
    footer {{
      margin-top: 3.5rem;
      padding-top: 1.25rem;
      border-top: 1px solid var(--rule);
      font-size: 0.78rem;
      color: var(--ink-light);
    }}

    footer ul {{
      list-style: none;
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem 1.25rem;
      margin-top: 0.4rem;
    }}

    footer a {{
      color: var(--ink-light);
      text-decoration: none;
      border-bottom: 1px solid var(--rule);
      transition: color 0.15s;
    }}
    footer a:hover {{ color: var(--accent); border-color: var(--accent); }}

    /* ── Responsive fine-tuning ───────────────────────── */
    @media (max-width: 480px) {{
      body {{ padding: 1.25rem 1rem 3rem; }}
      h1   {{ font-size: 2rem; }}
    }}
  </style>
</head>
<body>
  <div class="wrapper">

    <header>
      <p class="eyebrow">Briefing Quotidiano</p>
      <h1>Le notizie di oggi</h1>
      <p class="dateline">{date_it} &mdash; aggiornato alle {time_utc}</p>
    </header>

    <hr class="rule" />

    <article class="briefing-body">
      {paragraphs_html}
    </article>

    <footer>
      <p>Fonti:</p>
      <ul>{sources_list}</ul>
      <p style="margin-top:0.75rem">Generato automaticamente con Claude AI · contenuto sintetizzato, non editoriale.</p>
    </footer>

  </div>
</body>
</html>
"""


def main():
    print("📰 Briefing Quotidiano — avvio")

    print("\n1/3  Lettura feed RSS…")
    news = fetch_news()
    print(f"     Totale notizie raccolte: {len(news)}")

    print("\n2/3  Generazione briefing con Claude…")
    briefing = build_briefing(news)
    print(f"     Briefing generato ({len(briefing)} caratteri)")

    print("\n3/3  Scrittura index.html…")
    html = render_html(briefing)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("     ✓ index.html salvato")

    print("\n✅  Completato.")


if __name__ == "__main__":
    main()
