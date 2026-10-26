import pypdfium2 as pdfium

pdf = pdfium.PdfDocument('/home/GP282928/work/cases_pdf/USGS-SDG-040.pdf')
page = pdf[4]
tp = page.get_textpage()
raw = tp.get_text_range()

i = raw.find('Louis District')
print(repr(raw[i:i + 60]))
print([hex(ord(c)) for c in raw[i + 14:i + 22]])