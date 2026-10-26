import sys
sys.path.insert(0, '/home/GP282928/work/my_submission')

from participant_module.adapter import read_pages

pages = read_pages('/home/GP282928/work/cases_pdf/USGS-SDG-040.pdf')
print('pages:', len(pages))
print('page 5 start:', repr(pages[4][:200]))
print('hidden marker left anywhere?', '\ufffe' in ''.join(pages))

print("'District and' present?", 'District and' in pages[4])