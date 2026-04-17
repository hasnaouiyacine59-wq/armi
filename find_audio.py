import json, re, html, urllib.parse, urllib.request

with open('iframes_dump.json') as f:
    data = json.load(f)

audio_url = None
for frame in data:
    content = frame.get('content', '')
    m = re.search(r'<audio[^>]+id="audio-source"[^>]+src="([^"]+)"', content)
    if not m:
        m = re.search(r'<audio[^>]+src="([^"]+)"[^>]+id="audio-source"', content)
    if m:
        audio_url = html.unescape(m.group(1))
        break

if audio_url:
    encoded = urllib.parse.quote(audio_url, safe='')
    print('URL-encoded:', encoded)
    try:
        urllib.request.urlretrieve(audio_url, 'captcha_audio.mp3')
        print('Downloaded captcha_audio.mp3')
    except Exception as e:
        print(f'Download failed: {e}')
        input('r444')
else:
    print('audio-source not found')
