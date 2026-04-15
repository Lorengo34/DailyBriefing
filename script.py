import feedparser
import anthropic
import os
import re
from datetime import datetime

# ── Configurazione feed RSS ──────────────────────────────────────────────────
RSS_FEEDS = {
    "ANSA":         "https://www.ansa.it/sito/ansait_rss.xml",
    "Sky TG24":     "https://tg24.sky.it/rss/cronaca.xml",
    "Il Sole 24 Ore": "https://www.ilsole24ore.com/rss/mondo.xml",
}

# Ridotto a 10 per risparmiare token (meno dati in ingresso = meno costo)
MAX_ITEMS_PER_FEED = 10  

def fetch_news() -> list[dict]:
    news = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                summary = re.sub(r"\s{2,}", " ", summary)
                if title:
                    # Accorciamo ulteriormente il sommario inviato a Claude per risparmiare
                    news.append({"source": source, "title": title, "summary": summary[:200]})
            print(f"  ✓ {source}: {len(feed.entries[:MAX_ITEMS_PER_FEED])} notizie")
        except Exception as e:
            print(f"  ✗ Errore leggendo {source}: {e}")
    return news

def build_briefing(news: list[dict]) -> str:
    # Utilizzo del modello HAIKU (molto più economico)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    news_block = "\n\n".join(
        f"[{item['source']}] {item['title']}: {item['summary']}"
        for item in news
    )

    system_prompt = (
        "Sei un analista esperto. Crea un briefing discorsivo delle notizie di oggi. "
        "REGOLE IMPORTANTI:\n"
        "1. Dividi in paragrafi per temi (POLITICA, CRONACA, MONDO).\n"
        "2. NON usare elenchi puntati o liste.\n"
        "3. Usa il GRASSETTO (markdown: **parola**) per evidenziare le entità e i concetti chiave.\n"
        "4. Scarta duplicati e clickbait.\n"
        "5. Scrivi in italiano con un tono asciutto.\n"
        "6. I titoli delle sezioni devono essere in MAIUSCOLO e finire con i due punti."
    )

    message = client.messages.create(
        model="claude-3-haiku-20240307", # Modello super economico
        max_tokens=1500, # Aumentato per evitare tagli, ma Haiku costa pochissimo
        temperature=0,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Sintetizza in paragrafi con grassetti:\n\n{news_block}"}
        ],
    )
    return message.content[0].text

def render_html(briefing: str) -> str:
    now = datetime.utcnow()
    date_it = now.strftime("%-d %B %Y").replace("January","gennaio").replace("February","febbraio").replace("March","marzo").replace("April","aprile").replace("May","maggio").replace("June","giugno").replace("July","luglio").replace("August","agosto").replace("September","settembre").replace("October","ottobre").replace("November","novembre").replace("December","dicembre")
    time_utc = now.strftime("%H:%M UTC")

    import html as html_lib
    paragraphs_html = ""
    
    # Processiamo il testo per gestire grassetti e titoli
    for line in briefing.strip().split("\n"):
        line = line.strip()
        if not line: continue
        
        # Gestione Grassetto Markdown -> HTML
        line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line)
        
        # Se la linea è un titolo di sezione (MAIUSCOLO:)
        if line.isupper() and line.endswith(":"):
            paragraphs_html += f'<h2 class="section-title">{line}</h2>\n'
        else:
            paragraphs_html += f'<p>{line}</p>\n'

    sources_list = "".join(f'<li><a href="{url}">{name}</a></li>' for name, url in RSS_FEEDS.items())

    # (Qui rimane lo stile CSS che avevi già, ho aggiunto solo lo stile per lo strong)
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Briefing Quotidiano</title>
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap" rel="stylesheet" />
  <style>
    body {{ background: #faf8f4; color: #1a1a1a; font-family: 'Source Sans 3', sans-serif; line-height: 1.75; padding: 2rem 1.25rem; }}
    .wrapper {{ max-width: 680px; margin: 0 auto; }}
    header {{ border-top: 3px solid #1a1a1a; padding-top: 1rem; margin-bottom: 2rem; }}
    h1 {{ font-family: 'Libre Baskerville', serif; font-size: 2.5rem; }}
    .section-title {{ color: #c0392b; font-size: 0.8rem; letter-spacing: 0.1em; margin-top: 2rem; border-bottom: 1px solid #ddd8ce; }}
    p {{ font-family: 'Libre Baskerville', serif; margin-bottom: 1.2rem; }}
    strong {{ font-weight: 700; color: #000; }}
    footer {{ font-size: 0.8rem; margin-top: 3rem; border-top: 1px solid #ddd8ce; padding-top: 1rem; color: #555; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <header><h1>Le notizie di oggi</h1><p>{date_it} — {time_utc}</p></header>
    <article>{paragraphs_html}</article>
    <footer><p>Fonti: {sources_list}</p></footer>
  </div>
</body>
</html>"""

def main():
    print("📰 Avvio ottimizzato (Haiku)...")
    news = fetch_news()
    briefing = build_briefing(news)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render_html(briefing))
    print("✅ Completato.")

if __name__ == "__main__":
    main()
