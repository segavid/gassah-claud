import re
import json
import base64
import urllib.parse
import urllib.request
from urllib.request import Request, urlopen
from starlette.responses import Response

TARGET = "https://gesseh.net"
ROBOTS_TAG = "<meta name='robots' content='index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1' />"
GOOGLE_VERIFY = "<meta name='google-site-verification' content='HWrhtgkCPV2OT-OWRzV60Vdl1pWxt35-aEZ7NNDTHWs' />"
HEADER_BOX = """
<div style="width:100%;background:#ff004c;color:#fff;padding:15px;text-align:center;font-size:20px;font-weight:bold;direction:rtl;">
  <a href="https://z.3isk.news/all-turkish-series-esheeq/" title="مسلسلات تركية" style="color:#fff;text-decoration:none;">مسلسلات تركية مترجمة</a>
</div>
"""



def base64_decode(encoded_str):
    try:
        normalized = re.sub(r'\s+', '', encoded_str).replace('%3D', '=')
        normalized = normalized.replace('-', '+').replace('_', '/')
        padding = len(normalized) % 4
        if padding:
            normalized += '=' * (4 - padding)
        decoded_bytes = base64.b64decode(normalized)
        return urllib.parse.unquote(decoded_bytes.decode('utf-8'))
    except Exception:
        return None


def build_server_url(server):
    name = (server.get('name') or '').lower()
    server_id = server.get('id') or ''
    if re.match(r'^https?://', server_id, re.I):
        return server_id
    if 'estream' in name:
        return f"https://arabveturk.com/{server_id}.html"
    if 'arab' in name:
        return f"https://v.turkvearab.com/embed-{server_id}.html"
    if 'ok' in name:
        return f"https://ok.ru/videoembed/{server_id}"
    if 'red' in name:
        return f"https://iplayerhls.com/e/{server_id}"
    if 'dailymotion' in name:
        return f"https://www.dailymotion.com/embed/video/{server_id}"
    return server_id


def process_html(body, worker_domain, canonical_url):
    target_host = urllib.parse.urlparse(TARGET).hostname
    escaped = re.escape(target_host)
    body = re.sub(f'https?://{escaped}', worker_domain, body, flags=re.I)
    body = re.sub(f'//{escaped}', worker_domain, body, flags=re.I)
    body = re.sub(r'(src|href)=["\']/([^"\']+)["\']', rf'\1="{worker_domain}/\2"', body, flags=re.I)
    body = re.sub(r'<meta[^>]*name=[\'"]robots[\'"][^>]*>', '', body, flags=re.I)
    body = re.sub(r'<meta[^>]*name=[\'"]google-site-verification[\'"][^>]*>', '', body, flags=re.I)
    body = re.sub(r'<link[^>]*rel=[\'"]canonical[\'"][^>]*>', '', body, flags=re.I)
    body = re.sub(r'<head>', f'<head>\n{ROBOTS_TAG}\n{GOOGLE_VERIFY}\n<link rel="canonical" href="{canonical_url}" />', body, count=1, flags=re.I)
    body = HEADER_BOX + "\n" + body
    return body


# ✅ Proper async handler for Vercel Python Runtime
async def handler(request):
    try:
        url = str(request.url)
        parsed = urllib.parse.urlparse(url)
        worker_domain = f"{parsed.scheme}://{parsed.netloc}"
        canonical_url = worker_domain + parsed.path + (("?" + parsed.query) if parsed.query else "")
        upstream = TARGET + parsed.path + (("?" + parsed.query) if parsed.query else "")

        req_headers = {
            "Referer": TARGET,
            "User-Agent": request.headers.get("user-agent", "Mozilla/5.0")
        }

        req = Request(upstream, headers=req_headers)
        with urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            body = resp.read()

            if "text/html" in content_type:
                body_str = body.decode("utf-8", errors="ignore")
                processed = process_html(body_str, worker_domain, canonical_url)
                return Response(processed, media_type="text/html")

            if any(x in content_type for x in ["xml", "rss", "text/plain"]):
                body_str = body.decode("utf-8", errors="ignore")
                return Response(body_str, media_type="application/xml")

            return Response(body, media_type=content_type)

    except Exception as e:
        return Response(f"Error: {str(e)}", status_code=500, media_type="text/plain")

