import json
import base64
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

TARGET = "https://gesseh.net"
ROBOTS_TAG = "<meta name='robots' content='index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1' />"
GOOGLE_VERIFY = "<meta name='google-site-verification' content='HWrhtgkCPV2OT-OWRzV60Vdl1pWxt35-aEZ7NNDTHWs' />"
HEADER_BOX = """
<div style="width:100%;background:#ff004c;color:#fff;padding:15px;text-align:center;font-size:20px;font-weight:bold;direction:rtl;">
  <a href="https://z.3isk.news/all-turkish-series-esheeq/" style="color:#fff;text-decoration:none;">مسلسلات تركية مترجمة</a>
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
        decoded_str = urllib.parse.unquote(decoded_bytes.decode('utf-8'))
        return decoded_str
    except Exception:
        return None


def build_server_url(server):
    name = (server.get('name') or '').lower()
    server_id = server.get('id') or ''
    if re.match(r'^https?://', server_id, re.IGNORECASE):
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
    if 'express' in name:
        return server_id
    return server_id


def replace_embed_with_buttons(match, worker_domain):
    encoded_post = match.group(1)
    decoded = base64_decode(encoded_post)
    if not decoded:
        return match.group(0)
    try:
        data = json.loads(decoded)
    except json.JSONDecodeError:
        return match.group(0)
    servers = []
    for s in data.get('servers', []):
        url = build_server_url(s)
        if url:
            servers.append({'name': s.get('name', ''), 'url': url})
    if not servers:
        return match.group(0)
    buttons_html = []
    for s in servers:
        safe_url = s['url'].replace('"', '&quot;')
        safe_name = s['name'].replace('<', '&lt;').replace('>', '&gt;')
        buttons_html.append(f'<a href="{safe_url}" target="_blank" class="server-btn">{safe_name} - اضغط هنا للمشاهدة</a>')
    return f"""
<div class="servers-container">
  <style>
    .servers-container{{max-width:800px;margin:20px auto;padding:20px;background:#f5f5f5;border-radius:10px}}
    .server-btn{{display:block;background:#ff004c;color:#fff;padding:15px;margin:10px 0;text-align:center;text-decoration:none;border-radius:8px;font-size:18px;font-weight:bold;transition:all 0.3s}}
    .server-btn:hover{{background:#cc0039;transform:scale(1.02)}}
  </style>
  {''.join(buttons_html)}
</div>"""


def replace_fake_block_with_urls(match, worker_domain):
    enc_match = re.search(r'post=([^"\'\s]+)', match.group(0), re.IGNORECASE)
    if not enc_match:
        return match.group(0)
    decoded = base64_decode(enc_match.group(1))
    if not decoded:
        return match.group(0)
    try:
        data = json.loads(decoded)
    except json.JSONDecodeError:
        return match.group(0)
    servers = []
    for s in data.get('servers', []):
        url = build_server_url(s)
        if url:
            servers.append({'name': s.get('name', ''), 'url': url})
    if not servers:
        return match.group(0)
    servers_html = []
    for i, s in enumerate(servers):
        safe_url = s['url'].replace('"', '&quot;')
        safe_name = s['name'].replace('<', '&lt;').replace('>', '&gt;')
        servers_html.append(f"""
<div class="srv-row">
  <b>{safe_name}</b>
  <input type="text" readonly value="{safe_url}" class="srv-url" id="u{i}">
  <button onclick="navigator.clipboard.writeText(document.getElementById('u{i}').value);this.textContent='✓'">نسخ</button>
</div>""")
    player_html = f"""
<style>
.notice-bar{{background:#222;color:#fff;padding:10px;text-align:center;font-size:15px}}
.getEmbed{{max-width:800px;margin:0 auto;padding:10px}}
.srv-row{{display:flex;align-items:center;gap:6px;margin:5px 0;flex-wrap:wrap}}
.srv-row b{{min-width:70px;font-size:14px;flex-shrink:0}}
.srv-url{{width:300px;max-width:100%;padding:5px;font-size:11px;overflow:hidden;text-overflow:ellipsis}}
.srv-row button{{background:#ff004c;color:#fff;border:0;padding:5px 10px;cursor:pointer;border-radius:3px;font-size:13px;white-space:nowrap}}
.srv-row button:hover{{background:#222}}
@media(max-width:600px){{.srv-url{{width:200px}}}}
</style>
<div class="notice-bar">يرجى نسخ السيرفر وفتحه في المتصفح</div>
<div class="getEmbed">{''.join(servers_html)}</div>
"""
    return player_html + '<div class="singleInfo"'


def process_html(body, worker_domain, canonical_url):
    target_host = urllib.parse.urlparse(TARGET).hostname
    escaped_host = re.escape(target_host)
    body = re.sub(f'https?://{escaped_host}', worker_domain, body, flags=re.IGNORECASE)
    body = re.sub(f'//{escaped_host}', worker_domain, body, flags=re.IGNORECASE)
    body = re.sub(r'(src|href)=["\']/([^"\']+)["\']', rf'\1="{worker_domain}/\2"', body, flags=re.IGNORECASE)
    body = re.sub(r'href=["\']\/(?=(?:%d9%85|مسلسل|الحلقة)[^"\']*)', f'href="{worker_domain}/', body, flags=re.IGNORECASE)
    body = re.sub(r'<a\s+title="الرئيسية"\s+href="/">الرئيسية</a>', '<a title="قصة عشق الاصلي" href="https://z.3isk.news/video/">قصة عشق الاصلي</a>', body, flags=re.IGNORECASE)

    def decode_link(match):
        try:
            encoded = match.group(3)
            decoded = base64_decode(urllib.parse.unquote(encoded))
            if not decoded:
                return match.group(0)
            clean_url = re.sub(r'https?://(?:www\.)?gesseh\.net', worker_domain, decoded, flags=re.IGNORECASE)
            return f'<a {match.group(1)}href="{clean_url}"{match.group(4)}>'
        except Exception:
            return match.group(0)

    body = re.sub(r'<a\s+([^>]*?)href=(["\'])https?://arbandroid\.com/[^"\']+\?url=([^"\']+)\2([^>]*)>', decode_link, body, flags=re.IGNORECASE)
    body = re.sub(r'<div[^>]*class="[^"]*embed[^"]*"[^>]*>[\s\S]*?post=([^"\'&\s]+)[\s\S]*?</div>', lambda m: replace_embed_with_buttons(m, worker_domain), body, flags=re.IGNORECASE)
    body = re.sub(r'<script[^>]*type=["\']litespeed/javascript["\'][^>]*>[\s\S]*?</script>\s*<div class="secContainer bg">[\s\S]*?<div class="singleInfo"', lambda m: replace_fake_block_with_urls(m, worker_domain), body, flags=re.IGNORECASE)
    body = re.sub(r'<meta[^>]*name=[\'"]robots[\'"][^>]*>', '', body, flags=re.IGNORECASE)
    body = re.sub(r'<meta[^>]*name=[\'"]google-site-verification[\'"][^>]*>', '', body, flags=re.IGNORECASE)
    body = re.sub(r'<link[^>]*rel=[\'"]canonical[\'"][^>]*>', '', body, flags=re.IGNORECASE)
    body = re.sub(r'<head>', f'<head>\n{ROBOTS_TAG}\n{GOOGLE_VERIFY}\n<link rel="canonical" href="{canonical_url}" />', body, count=1, flags=re.IGNORECASE)
    body = HEADER_BOX + "\n" + body
    return body


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        query_string = ''
        if '?' in path:
            path, query_string = path.split('?', 1)
            query_string = '?' + query_string
        
        worker_domain = f"https://{self.headers.get('Host', 'your-domain.com')}"
        canonical_url = f"{worker_domain}{path}{query_string}"
        upstream = TARGET + path + query_string
        
        req_headers = {
            'Referer': TARGET,
            'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0')
        }
        
        try:
            req = urllib.request.Request(upstream, headers=req_headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                body = response.read()
                
                if 'text/html' in content_type:
                    body_str = body.decode('utf-8', errors='ignore')
                    processed_body = process_html(body_str, worker_domain, canonical_url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF-8')
                    self.end_headers()
                    self.wfile.write(processed_body.encode('utf-8'))
                    return
                
                if 'xml' in content_type or 'rss' in content_type or 'text/plain' in content_type:
                    body_str = body.decode('utf-8', errors='ignore')
                    target_host = urllib.parse.urlparse(TARGET).hostname
                    escaped_host = re.escape(target_host)
                    body_str = re.sub(f'https?://{escaped_host}', worker_domain, body_str, flags=re.IGNORECASE)
                    body_str = re.sub(f'//{escaped_host}', worker_domain, body_str, flags=re.IGNORECASE)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/xml; charset=UTF-8')
                    self.end_headers()
                    self.wfile.write(body_str.encode('utf-8'))
                    return
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(body)
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Error: {str(e)}'.encode('utf-8'))
