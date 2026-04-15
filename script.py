import feedparser
import anthropic
import os
import re
from datetime import datetime

# -- Configurazione feed RSS --
RSS_FEEDS = {
    "ANSA": "https://www.ansa.it/sito/ansait_rss.xml",
    "Sky TG24": "https://tg24.sky.it/rss/cronaca.xml",
    "Il Sole 24 Ore": "https://www.ilsole24ore.com/rss/mondo.xml",
}

MAX_ITEMS_PER_FEED = 15

def fetch_news() -> list[dict]:
    news = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
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
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    news_block = "\n\n".join(
        f"[{item['source']}]\nTitolo: {item['title']}\nSommario: {item['summary']}"
        for item in news
    )
    system_prompt = (
        "Sei un giornalista analitico. Crea un briefing delle notizie più importanti di oggi "
        "in circa 600 parole. Usa un tono asciutto, evita il clickbait, raggruppa le notizie "
        "per temi (Politica, Cronaca, Mondo) e scarta i duplicati. "
        "Scrivi in italiano. Usa il grassetto markdown (es: **parola**) per i concetti chiave. "
        "Non usare elenchi. I titoli delle sezioni devono essere in maiuscolo seguiti da due punti."
    )
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Ecco le notizie di oggi:\n\n{news_block}"}],
    )
    return message.content[0].text

def render_html(briefing: str) -> str:
    now = datetime.utcnow()
    date_it = now.strftime("%-d %B %Y").replace("January","gennaio").replace("February","febbraio").replace("March","marzo").replace("April","aprile").replace("May","maggio").replace("June","giugno").replace("July","luglio").replace("August","agosto").replace("September","settembre").replace("October","ottobre").replace("November","novembre").replace("December","dicembre")
    time_utc = now.strftime("%H:%M UTC")
    import html as html_lib
    paragraphs_html = ""
    for line in briefing.strip().split("\n"):
        line = line.strip()
        if not line: continue
        
        # Converte il grassetto **testo** in <strong>testo</strong>
        line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line)
        
        if line.isupper() or (line.endswith(":") and len(line) < 40 and line == line.upper()):
            paragraphs_html += f'<h2 class="section-title">{line}</h2>\n'
        else:
            paragraphs_html += f'<p>{line}</p>\n'
            
    sources_list = "".join(f'<li><a href="{url}" target="_blank">{name}</a></li>' for name, url in RSS_FEEDS.items())
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Briefing — {date_it}</title>
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap" rel="stylesheet" />
  <style>
    body {{ background: #faf8f4; color: #1a1a1a; font-family: 'Source Sans 3', sans-serif; line-height: 1.75; padding: 2rem 1.25rem; }}
    .wrapper {{ max-width: 680px; margin: 0 auto; }}
    header {{ border-top: 3px solid #1a1a1a; padding-top: 2rem; margin-bottom: 2.5rem; }}
    h1 {{ font-family: 'Libre Baskerville', serif; font-size: 2.5rem; font-weight: 700; }}
    .section-title {{ color: #c0392b; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.15em; margin-top: 2.2rem; border-bottom: 1px solid #ddd8ce; }}
    p {{ font-family: 'Libre Baskerville', serif; margin-bottom: 1.1rem; }}
    strong {{ font-weight: 700; color: #000; }}
    footer {{ margin-top: 3.5rem; padding-top: 1rem; border-top: 1px solid #ddd8ce; font-size: 0.8rem; color: #555; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <header><h1>Le notizie di oggi</h1><p>{date_it} — {time_utc}</p></header>
    <article class="briefing-body">{paragraphs_html}</article>
    <footer><p>Fonti: {sources_list}</p></footer>
  </div>
</body>
</html>"""

def main():
    print("📰 Avvio...")
    news = fetch_news()
    briefing = build_briefing(news)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render_html(briefing))
    print("✅ Completato.")

if __name__ == "__main__":
    main()
