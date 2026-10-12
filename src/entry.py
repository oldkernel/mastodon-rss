from workers import Response, WorkerEntrypoint, fetch
from urllib.parse import urlparse, parse_qs
from datetime import datetime


INSTANCE = "https://mastodon.social"
DEFAULT_HASHTAG = "linux"
DEFAULT_LANGUAGE = "it"
MAX_POSTS = 30



async def fetch_posts(hashtag, language):
    base_url = (
        f"{INSTANCE}/api/v1/timelines/tag/{hashtag}"
    )

    filtered = []
    seen = set()
    max_id = None
    max_pages = 5

    for _ in range(max_pages):
        url = f"{base_url}?limit=40"

        if max_id:
            url += f"&max_id={max_id}"

        response = await fetch(url)

        if not response.ok:
            raise RuntimeError(
                f"Mastodon API error: {response.status}"
            )

        posts = await response.json()

        #print(
        #    f"Pagina richiesta: {max_id or 'iniziale'}"
        #    f" | Post ricevuti: {len(posts)}"
        #    f" | Post in lingua {language}: "
        #    f"{sum(1 for p in posts if p.get('language') == language)}"
        #

        if not posts:
            break

        for post in posts:
            post_id = post.get("id")

            if not post_id or post_id in seen:
                continue

            seen.add(post_id)

            if post.get("language") == language:
                filtered.append(post)

        if len(filtered) >= MAX_POSTS:
            break

        # Se Mastodon restituisce meno di 40 post,
        # probabilmente siamo arrivati alla fine.
        if len(posts) < 40:
            break

        last_id = posts[-1].get("id")

        if not last_id or last_id == max_id:
            break

        max_id = last_id

    filtered.sort(
        key=lambda post: post.get("created_at", ""),
        reverse=True,
    )

    return filtered[:MAX_POSTS]

def escape_xml(value):
    value = str(value or "")
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def make_rss(posts, hashtag, language):
    items = []

    for post in posts:
        account = post.get("account", {})
        username = account.get("acct", "utente")
        content = post.get("content", "")
        post_url = post.get("url", "")
        created_at = post.get("created_at", "")
        post_id = post.get("id", post_url)

        try:
            date = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )
            pub_date = date.strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )
        except (ValueError, TypeError):
            pub_date = ""

        items.append(f"""
    <item>
      <title>{escape_xml("Post di @" + username)}</title>
      <link>{escape_xml(post_url)}</link>
      <guid isPermaLink="false">{escape_xml(post_id)}</guid>
      <description>{escape_xml(content)}</description>
      {f"<pubDate>{pub_date}</pubDate>" if pub_date else ""}
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>#{escape_xml(hashtag)} — Mastodon RSS</title>
    <link>{INSTANCE}/tags/{escape_xml(hashtag)}</link>
    <description>Post in lingua {escape_xml(language)} da {INSTANCE}</description>
    <language>{escape_xml(language)}</language>
    {''.join(items)}
  </channel>
</rss>
"""


async def handle_request(request, cache):
    parsed = urlparse(request.url)

    if parsed.path == "/feed.xml":
        params = parse_qs(parsed.query)

        hashtag = params.get(
            "tag", [DEFAULT_HASHTAG]
        )[0].lstrip("#")

        language = params.get(
            "lang", [DEFAULT_LANGUAGE]
        )[0].lower()

        if (
            not hashtag
            or len(hashtag) > 100
            or not all(
                char.isalnum() or char in "_-"
                for char in hashtag
            )
        ):
            return Response(
                "Hashtag non valido",
                status=400,
            )

        if (
            len(language) not in (2, 3)
            or not language.isalpha()
        ):
            return Response(
                "Codice lingua non valido",
                status=400,
            )

        cache_key = f"feed:{hashtag.lower()}:{language}"

        # Prova a recuperare il feed dalla cache.
        try:
            cached_feed = await cache.get(cache_key)

            if cached_feed is not None:
                print(f"Cache HIT: {cache_key}")

                return Response(
                    cached_feed,
                    headers={
                        "content-type":
                            "application/rss+xml; charset=utf-8"
                    },
                )

        except Exception as exc:
            print(f"Errore lettura cache: {exc}")

        print(f"Cache MISS: {cache_key}")

        # Se non c'è una copia valida, interroga Mastodon.
        posts = await fetch_posts(hashtag, language)
        rss = make_rss(posts, hashtag, language)

        # Conserva il feed per 30 minuti.
        try:
            await cache.put(
                cache_key,
                rss,
                expirationTtl=1800,
            )
        except Exception as exc:
            print(f"Errore scrittura cache: {exc}")

        return Response(
            rss,
            headers={
                "content-type":
                    "application/rss+xml; charset=utf-8"
            },
        )

    return Response(
        "Mastodon RSS attivo. Usa /feed.xml?tag=linux&lang=it",
        headers={
            "content-type": "text/plain; charset=utf-8"
        },
    )



class Default(WorkerEntrypoint):
    async def fetch(self, request):
        try:
            return await handle_request(request, self.env.FEED_CACHE)
        except Exception:
            return Response(
                "Errore durante la generazione del feed. Riprova più tardi.",
                status=502,
                headers={"content-type": "text/plain; charset=utf-8"},
            )