"""Bounded direct extraction/image decoding child; never executes document content."""
import base64
import json
import sys


def extract(payload):
    import io
    data = base64.b64decode(payload['data'], validate=True)
    if payload.get('image_path'):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = 16000000
        if len(data) > 10*1024*1024: raise ValueError('Image exceeds 10 MiB')
        with Image.open(io.BytesIO(data)) as picture:
            if picture.format not in {'PNG','JPEG','WEBP'}: raise ValueError('Unsupported image format')
            if picture.width*picture.height>16000000: raise ValueError('Image exceeds 16 megapixels')
            picture.load()
            picture.thumbnail((2500,2500))
            picture.convert('RGB').save(payload['image_path'],'PNG')
        return [{'page':1,'text':'','needs_ocr':True,'extraction':'image'}]
    if len(data) > 10 * 1024 * 1024 or not data.startswith(b'%PDF-'):
        raise ValueError('Invalid or oversized PDF')
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported')
    if len(reader.pages) > 200:
        raise ValueError('PDF exceeds 200 pages')
    segments = []
    total = 0
    for index, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ''
        total += len(text.encode('utf-8'))
        if total > 1000000:
            raise ValueError('Extracted PDF text exceeds 1 MiB')
        # Captions alone do not make a screenshot-heavy PDF readable.
        objects=page.get('/Resources',{}).get('/XObject',{})
        has_images=any(obj.get_object().get('/Subtype') in {'/Image','/Form'} for obj in objects.get_object().values()) if objects else False
        segments.append({'page':index, 'text':text, 'needs_ocr':has_images or len(text.strip())<80,
                         'extraction':'direct_text'})
    return segments


if __name__ == '__main__':
    try:
        if sys.platform != 'win32':
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (768*1024*1024, 768*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU, (25,25))
        print(json.dumps({'ok':True,'segments':extract(json.load(sys.stdin))}))
    except ImportError:
        print(json.dumps({'ok':False,'error':'PDF extraction requires pypdf in the configured document interpreter'}))
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
