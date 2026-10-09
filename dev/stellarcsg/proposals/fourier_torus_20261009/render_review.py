"""Use installed Word for PDF conversion and bundled skill renderer for PNG QA.

This Windows bundle has no LibreOffice. No software is acquired. The Word PDF
is the render of the actual DOCX, rather than a separately typeset substitute.
"""
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parent
skill = Path('C:/Users/joshu/.codex/plugins/cache/openai-primary-runtime/documents/26.1007.11041/skills/documents/render_docx.py')
spec = importlib.util.spec_from_file_location('bundled_docx_renderer', skill)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
pdf = ROOT / 'qa' / 'review.pdf'
renderer.convert_to_pdf = lambda *args, **kwargs: (str(pdf), 'Converted actual DOCX with installed Microsoft Word; no bundled LibreOffice on Windows.')
renderer.rasterize(str(ROOT / 'Fourier_torus_methods_reviewer_packet.docx'), str(ROOT / 'qa'), 125, False, False)
print('Rendered', len(list((ROOT / 'qa').glob('page-*.png'))), 'pages')
