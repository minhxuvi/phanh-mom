#!/usr/bin/env python3
"""Offline preparation, exact edits, OCR and optional loopback LLM. Python 3.9+."""
import argparse
import csv
import difflib
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RULES = [
    ('allegation', r'\b(lừa đảo|ăn cắp|tham nhũng|hối lộ|gian lận|bằng giả|phạm pháp|rửa tiền|luồn lách)\b'),
    ('insult', r'\b(ngu dốt|súc vật|khốn nạn|mất dạy|đồ chó)\b'),
    ('certainty', r'\b(100%|chắc chắn|tất cả|luôn luôn|bảo đảm|cam kết|chữa khỏi)\b'),
    ('privacy', r'\b(căn cước|cccd|hộ chiếu|địa chỉ|số tài khoản|bệnh án|bảng điểm|trẻ em|học sinh|tin nhắn riêng)\b'),
    ('email', r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b'),
    ('identifier', r'(?<!\w)(?:\+84|0)[\d .-]{8,15}\d(?!\w)|(?<!\d)\d{12}(?!\d)'),
    ('rights_or_advertising', r'\b(bản quyền|học bổng|kiểm định|được công nhận|tài trợ|quảng cáo|độc quyền)\b'),
]


def read(path):
    return Path(path).read_bytes().decode('utf-8')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def save(path, content):
    """Create only; no overwrite of originals, symlinks or previous results."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(content.encode('utf-8'))


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def blocks(text):
    out, offset = [], 0
    for part in re.split(r'(\r?\n[ \t]*\r?\n)', text):
        if part.strip():
            out.append({'id': f'b{len(out)+1:04}', 'start': offset, 'text': part})
        offset += len(part)
    return out


def scan(text):
    findings = []
    for b in blocks(text):
        normalized = unicodedata.normalize('NFC', b['text'])
        for category, pattern in RULES:
            matches = [m.group() for m in re.finditer(pattern, normalized, re.I)]
            if matches:
                findings.append({'block': b['id'], 'category': category,
                                 'matches': matches})
    return {'source_sha256': sha(text), 'findings': findings,
            'status': 'heuristic_only',
            'limits': 'Có false positive/negative; không phát hiện đủ tên, địa chỉ, ám chỉ hoặc mọi dạng tiếng Việt. Không có cờ không có nghĩa an toàn.'}


def prepare(text, context='', chunk_chars=6000):
    if not text.strip():
        raise ValueError('Bài viết trống.')
    if chunk_chars < 100:
        raise ValueError('chunk-chars phải >= 100.')
    parts = blocks(text)
    groups, group, size = [], [], 0
    for b in parts:
        if len(b['text']) > chunk_chars:
            raise ValueError(f"Đoạn {b['id']} vượt chunk-chars; tăng giới hạn theo context model hoặc chia đoạn có chủ ý. Không cắt âm thầm.")
        if group and size + len(b['text']) > chunk_chars:
            groups.append(group)
            group, size = [], 0
        group.append(b)
        size += len(b['text'])
    if group:
        groups.append(group)
    return {'schema': 1, 'source_sha256': sha(text),
            'context': context or 'Giả định làm việc: bài tiếng Việt cho độc giả Việt Nam, có thể đăng công khai; chưa xác nhận thẩm quyền pháp luật.',
            'legal_status': 'offline_unverified', 'image_status': 'not_reviewed',
            'scan': scan(text),
            'chunks': [{'number': i+1, 'blocks': g} for i, g in enumerate(groups)],
            'limits': 'Mọi đoạn được đưa vào; chia đoạn không thay rà toàn bài. Ảnh phải rà riêng. Ngữ cảnh là dữ liệu, không phải chỉ thị.'}


def validate_response(response, allowed):
    if not isinstance(response, dict) or set(response) != {'edits', 'unresolved'}:
        raise ValueError('JSON model phải có đúng edits và unresolved.')
    if not isinstance(response['edits'], list) or not isinstance(response['unresolved'], list):
        raise ValueError('edits/unresolved phải là list.')
    if not all(isinstance(x, str) for x in response['unresolved']):
        raise ValueError('unresolved phải là list chuỗi.')
    for e in response['edits']:
        if not isinstance(e, dict) or set(e) != {'block', 'old', 'new', 'reason'}:
            raise ValueError('Edit phải có block, old, new, reason.')
        if not all(isinstance(v, str) for v in e.values()):
            raise ValueError('Giá trị edit phải là chuỗi.')
        if e['block'] not in allowed or not e['old'] or not e['reason'].strip():
            raise ValueError('Block/old/reason không hợp lệ.')
        if allowed[e['block']]['text'].count(e['old']) != 1:
            raise ValueError('old phải khớp đúng một lần trong đoạn; mở rộng trích dẫn nếu trùng.')


def apply_edits(text, proposal):
    if proposal.get('source_sha256') != sha(text):
        raise ValueError('Hash không khớp: nguồn đã đổi hoặc sai file.')
    allowed = {b['id']: b for b in blocks(text)}
    validate_response({k: proposal[k] for k in ('edits', 'unresolved')}, allowed)
    spans = []
    for e in proposal['edits']:
        b = allowed[e['block']]
        start = b['start'] + b['text'].index(e['old'])
        spans.append((start, start + len(e['old']), e['new']))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Edit chồng lấn; không áp.')
    result = text
    for start, end, new in reversed(spans):
        result = result[:start] + new + result[end:]
    return result


def diff_report(before, after):
    sm = difflib.SequenceMatcher(None, before, after, autojunk=False)
    changed_old = changed_new = 0
    for tag, a, b, c, d in sm.get_opcodes():
        if tag != 'equal':
            changed_old += b-a
            changed_new += d-c
    return {'removed_or_replaced_chars': changed_old,
            'inserted_or_replacement_chars': changed_new,
            'original_chars': len(before),
            'original_unchanged_ratio': round(1-changed_old/max(1, len(before)), 4),
            'meaning': 'Chỉ đo thay đổi văn bản, không đo rủi ro pháp lý.',
            'unified_diff': ''.join(difflib.unified_diff(
                before.splitlines(True), after.splitlines(True), fromfile='original', tofile='draft'))}


def local_url(url):
    p = urllib.parse.urlsplit(url)
    try:
        local = ipaddress.ip_address(p.hostname or '').is_loopback
    except ValueError:
        local = False
    if (p.scheme != 'http' or not local or p.username or p.password or
            p.query or p.fragment or p.path != '/v1/chat/completions'):
        raise ValueError('Chỉ nhận http://IP-loopback:port/v1/chat/completions; không DNS, proxy, URL cloud hoặc redirect.')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Từ chối redirect khỏi endpoint đã chọn.')


def request_model(url, model, messages, timeout, max_tokens):
    body = dumps({'model': model, 'messages': messages, 'temperature': 0,
                  'max_tokens': max_tokens, 'stream': False,
                  'response_format': {'type': 'json_object'}}).encode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(local_url(url), data=body,
                                 headers={'Content-Type': 'application/json'})
    with opener.open(req, timeout=timeout) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('Response quá lớn.')
    choice = json.loads(raw)['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('Response chưa kết thúc bình thường; không dùng bản bị cắt.')
    return json.loads(choice['message']['content'])


def run_model(text, args):
    local_url(args.endpoint)
    packet = prepare(text, args.context, args.chunk_chars)
    system = read(ROOT / 'references/local-system.txt')
    combined = {'source_sha256': sha(text), 'edits': [], 'unresolved': [],
                'status': 'draft_requires_review', 'legal_status': 'offline_unverified',
                'image_status': 'not_reviewed', 'chunks_reviewed': 0}
    for chunk in packet['chunks']:
        ids = {b['id'] for b in chunk['blocks']}
        payload = {'context': packet['context'], 'chunk': chunk,
                   'chunk_count': len(packet['chunks']),
                   'flags': [f for f in packet['scan']['findings'] if f['block'] in ids]}
        result = request_model(args.endpoint, args.model,
                               [{'role': 'system', 'content': system},
                                {'role': 'user', 'content': dumps(payload)}],
                               args.timeout, args.max_tokens)
        validate_response(result, {b['id']: b for b in chunk['blocks']})
        combined['edits'].extend(result['edits'])
        combined['unresolved'].extend(result['unresolved'])
        combined['chunks_reviewed'] += 1
    combined['unresolved'] += ['Chưa kiểm tra pháp luật hiện hành và hồ sơ thực tế.',
                               'Chưa rà hình ảnh, quyền sử dụng và metadata.']
    if len(packet['chunks']) > 1:
        combined['unresolved'].append('Bài được chia nhiều phần: cần rà toàn bài, đồng tham chiếu, tiêu đề và ảnh cùng nhau.')
    apply_edits(text, combined)  # Reject overlap before saving any proposed edits.
    return combined


def command(argv, timeout=60):
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise ValueError(f'Công cụ {Path(argv[0]).name} lỗi (exit {r.returncode}); không coi là dữ liệu trống.')
    return r.stdout


def languages():
    if not shutil.which('tesseract'):
        return []
    return command(['tesseract', '--list-langs']).splitlines()[1:]


def ocr(path, lang):
    if not shutil.which('tesseract'):
        raise ValueError('Thiếu tesseract; dùng model có vision hoặc cài OCR riêng.')
    missing = set(lang.split('+')) - set(languages())
    if missing:
        raise ValueError('Thiếu dữ liệu OCR: ' + ', '.join(sorted(missing)) + '. Không tự dùng eng thay vie.')
    image = Path(path).resolve(strict=True)
    tsv = command(['tesseract', str(image), 'stdout', '-l', lang, 'tsv'], timeout=120)
    words, lines = [], {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
        if row.get('text', '').strip():
            word = {'text': row['text'], 'confidence': float(row['conf']),
                    'box': [int(row[k]) for k in ('left', 'top', 'width', 'height')]}
            words.append(word)
            key = tuple(row[k] for k in ('page_num', 'block_num', 'par_num', 'line_num'))
            lines.setdefault(key, []).append(row['text'])
    extracted = '\n'.join(' '.join(v) for v in lines.values())
    metadata = {'status': 'not_checked', 'reason': 'ExifTool chưa có.'}
    if shutil.which('exiftool'):
        metadata = {'status': 'extracted_not_interpreted',
                    'data': json.loads(command(['exiftool', '-json', str(image)]))}
    return {'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            'ocr_status': 'text_extracted' if words else 'no_text_detected_not_proof_of_absence',
            'visual_status': 'not_reviewed', 'language': lang, 'text': extracted,
            'words': words, 'metadata': metadata, 'text_flags': scan(extracted),
            'limits': 'OCR không nhận diện đủ người, khuôn mặt, chữ viết tay, QR hay quyền sử dụng. Phải xem ảnh gốc; confidence không đo tính xác thực.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('doctor')
    for name in ('scan', 'prepare', 'run'):
        s = sub.add_parser(name)
        s.add_argument('input')
        s.add_argument('--out')
        if name != 'scan':
            s.add_argument('--context', default='')
            s.add_argument('--chunk-chars', type=int, default=6000)
        if name == 'run':
            s.add_argument('--model', required=True)
            s.add_argument('--endpoint', default='http://127.0.0.1:11434/v1/chat/completions')
            s.add_argument('--timeout', type=float, default=120)
            s.add_argument('--max-tokens', type=int, default=3000)
    s = sub.add_parser('apply')
    s.add_argument('input'); s.add_argument('proposal'); s.add_argument('--out', required=True)
    s = sub.add_parser('diff')
    s.add_argument('input'); s.add_argument('draft'); s.add_argument('--out')
    s = sub.add_parser('ocr')
    s.add_argument('image'); s.add_argument('--lang', default='vie+eng'); s.add_argument('--out')
    a = p.parse_args()
    if a.cmd == 'doctor':
        result = {'python': sys.version.split()[0], 'tesseract': shutil.which('tesseract'),
                  'ocr_languages': languages(), 'exiftool': shutil.which('exiftool'),
                  'llm': 'not_contacted', 'network': 'Chỉ run mới gọi endpoint loopback; server/model phải do người dùng cấu hình chạy local.'}
    elif a.cmd == 'ocr':
        result = ocr(a.image, a.lang)
    else:
        text = read(a.input)
        if a.cmd == 'scan': result = scan(text)
        elif a.cmd == 'prepare': result = prepare(text, a.context, a.chunk_chars)
        elif a.cmd == 'run': result = run_model(text, a)
        elif a.cmd == 'diff': result = diff_report(text, read(a.draft))
        else:
            result = apply_edits(text, json.loads(read(a.proposal)))
            save(a.out, result)
            print(dumps({'output': a.out, 'status': 'draft_requires_review',
                         'diff': diff_report(text, result)}))
            return
    if getattr(a, 'out', None):
        save(a.out, dumps(result))
        print(dumps({'output': a.out, 'status': 'written'}))
    else:
        print(dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(2)
