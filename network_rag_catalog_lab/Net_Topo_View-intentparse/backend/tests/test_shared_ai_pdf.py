"""Exercise the real bounded extractor with a separately configured existing runtime."""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from llm.gateway_documents import extract_pdf


def text_pdf():
    content=b'BT /F1 12 Tf 50 700 Td (OSPF_DOCUMENTATION_MARKER) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream']
    output=b'%PDF-1.4\n';offsets=[]
    for index,obj in enumerate(objects,1):
        offsets.append(len(output));output+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(output)
    output+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets)
    return output+b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'


@unittest.skipUnless(os.getenv('COGNISHIELD_DOCUMENT_PYTHON'),'Configure an existing pypdf runtime explicitly')
class PDFTests(unittest.TestCase):
    def test_real_extraction_and_page_reference(self):
        segments=extract_pdf(text_pdf())
        self.assertEqual(segments[0]['page'],1)
        self.assertIn('OSPF_DOCUMENTATION_MARKER',segments[0]['text'])

    def test_invalid_pdf_has_no_binary_fallback(self):
        with self.assertRaises(HTTPException) as error: extract_pdf(b'%PDF-1.4 invalid')
        self.assertEqual(error.exception.status_code,422)


if __name__=='__main__': unittest.main()
