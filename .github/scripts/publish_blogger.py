#!/usr/bin/env python3
import html
import os
import pathlib
import re
import sys
import urllib.request
import urllib.error
import json

API = 'https://www.googleapis.com/blogger/v3'
BLOG_ID = os.environ.get('BLOGGER_BLOG_ID')
TOKEN = os.environ.get('BLOGGER_ACCESS_TOKEN')

if not BLOG_ID or not TOKEN:
    raise SystemExit('Missing BLOGGER_BLOG_ID or BLOGGER_ACCESS_TOKEN GitHub secret.')


def parse_markdown(path):
    text = path.read_text(encoding='utf-8')
    title = path.stem.replace('-', ' ').replace('_', ' ').title()
    labels = []
    video = ''
    image = ''
    body = text

    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) == 3:
            front = parts[1]
            body = parts[2].lstrip('\n')
            for line in front.splitlines():
                if ':' not in line:
                    continue
                k, v = line.split(':', 1)
                k = k.strip().lower()
                v = v.strip().strip('"\'')
                if k == 'title': title = v
                elif k == 'video': video = v
                elif k == 'image': image = v
                elif k == 'labels': labels = [x.strip() for x in v.split(',') if x.strip()]

    # Lightweight Markdown-to-HTML conversion for tutorial posts.
    body = html.escape(body)
    body = re.sub(r'&lt;iframe([\s\S]*?)&lt;/iframe&gt;', r'<iframe\1></iframe>', body)
    body = re.sub(r'&lt;(https?://[^&]+)&gt;', r'<a href="\1">\1</a>', body)
    body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', body, flags=re.M)
    body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', body, flags=re.M)
    body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', body, flags=re.M)
    body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', body)
    body = re.sub(r'`(.+?)`', r'<code>\1</code>', body)
    body = re.sub(r'^- (.+)$', r'<li>\1</li>', body, flags=re.M)
    body = re.sub(r'\n{2,}', '</p><p>', body)
    body = '<p>' + body.replace('\n', '<br>') + '</p>'

    if image:
        body = f'<p><img src="{html.escape(image, quote=True)}" alt="{html.escape(title, quote=True)}" style="max-width:100%;height:auto;"></p>' + body
    if video:
        body += f'<p><strong>Video Tutorial:</strong> <a href="{html.escape(video, quote=True)}">Watch the video</a></p>'

    return title, labels, body


def request(method, url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Bearer {TOKEN}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')
        raise SystemExit(f'Blogger API error {e.code}: {detail}')


def publish(path):
    title, labels, content = parse_markdown(path)
    slug = path.stem
    posts = request('GET', f'{API}/blogs/{BLOG_ID}/posts?maxResults=500')
    existing = next((p for p in posts.get('items', []) if p.get('labels') and slug in p.get('labels', [])), None)
    payload = {'kind':'blogger#post', 'title':title, 'content':content, 'labels':labels + [slug]}
    if existing:
        result = request('PUT', f"{API}/blogs/{BLOG_ID}/posts/{existing['id']}", payload)
        print(f'Updated: {title} ({result.get("url", "")})')
    else:
        result = request('POST', f'{API}/blogs/{BLOG_ID}/posts/', payload)
        print(f'Created: {title} ({result.get("url", "")})')


root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'tutorials')
files = sorted(root.glob('*.md'))
if not files:
    print('No tutorial Markdown files found.')
    raise SystemExit(0)
for path in files:
    publish(path)
