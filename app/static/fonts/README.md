# Fonts directory

To enable bilingual (English/Arabic) labels on generated PDFs (admission
forms, receipts, reports), add a Unicode Arabic-capable TrueType font here
named exactly:

    NotoNaskhArabic-Regular.ttf

A good free option is Google's Noto Naskh Arabic:
https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic

Download the Regular weight `.ttf` file and place it in this folder. No
code changes are needed - `app/services/document_branding.py` will detect
and register it automatically the next time a PDF is generated.

Without this file, PDFs still generate correctly - Arabic labels are
simply omitted (English-only) rather than rendering as blank/broken
glyphs. Full bidi/shaping correctness (so Arabic text reads right-to-left
and letters connect properly) additionally requires the `arabic-reshaper`
and `python-bidi` Python packages; add them to requirements.txt and wrap
Arabic strings with them in document_branding.py if/when full RTL
rendering is needed.
