# -*- coding: utf-8 -*-

import sys
sys.path.append('..')

project = u'ufit'
copyright = u'2013, Georg Brandl'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest',
              'sphinx.ext.intersphinx']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

version = release = '1.0'

exclude_patterns = ['_build']
pygments_style = 'sphinx'

html_theme = 'haiku'
html_title = 'ufit documentation'
#html_static_path = ['_static']

latex_documents = [
  ('index', 'ufit.tex', u'ufit Documentation',
   u'Georg Brandl', 'manual'),
]

intersphinx_mapping = {'http://docs.python.org/2/': None}
