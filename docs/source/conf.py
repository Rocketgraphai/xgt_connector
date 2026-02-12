# -*- coding: utf-8 -*- --------------------------------------------------===#
#
#  Copyright 2022-2026 Trovares Inc. dba Rocketgraph.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===----------------------------------------------------------------------===#

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from docutils import nodes

sys.path.insert(0, os.path.abspath('../../src'))
print(f"Sys.path: {sys.path}")

# -- Project information -----------------------------------------------------

project = 'xgt_connector'
copyright = '2022-2026 Trovares Inc. dba Rocketgraph'
author = 'rocketgraph.com'

# The full version, including alpha/beta/rc tags
release = '2.6.6'

# -- General configuration ---------------------------------------------------

# Sphinx extensions. These are Python module names that will be imported.
extensions = [
  'sphinx.ext.autodoc',
  'sphinx.ext.autosummary',
  'sphinx.ext.napoleon',
  'sphinx.ext.mathjax',
  'sphinx.ext.viewcode',
  'myst_nb',
  'sphinx_copybutton',
]
mathjax_path = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-AMS-MML_HTMLorMML'

# Combined with the ".. autosummary" directive in rST files and the
# sphinx-apidoc program, this option enables building separate pages for
# each entity requested under the autosummary directive.
autosummary_generate = True

# We generally don't want to document the whole module (since we only have one),
# but we *do* want to generate entries for class methods and attributes
# (members). Note: even though this is an autodoc setting and not an autosummary
# one, it still applies, since sphinx-apidoc simply creates autodoc directives
# in its separate files.
autodoc_default_options = {
  'no-modules': True,
  'members': True,
  'inherited-members': True,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'alabaster'
html_theme = 'pydata_sphinx_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_js_files = ["rocketgraph-icon.js", "pypi-icon.js"]

# Combined with the ".. autosummary" directive in rST files and the
# sphinx-apidoc program, this option enables building separate pages for
# each entity requested under the autosummary directive.
autosummary_generate = True

# By default, Sphinx likes to show the .rST source file that created the page.
# Since we auto-generated these with autosummary directives, they're useless.
html_show_sourcelink = False

# These options are specific to the 'sphinx_book_theme' currently used. If/when
# we switch to a custom theme, this will change or may go away entirely.
html_theme_options = {
  'use_edit_page_button': False,
  'show_toc_level': 2,
  "external_links": [
    {
      "url": "https://rocketgraph.com/",
      "name": "Rocketgraph Website",
    },
    {
      "url": "https://docs.rocketgraph.com/",
      "name": "Rocketgraph xGT",
    },
  ],
  "header_links_before_dropdown": 4,
  'logo': {
    'image_ligh': '_static/logo-light.svg',
    'image_dark': '_static/logo-dark.svg',
  },
  "icon_links": [
    {
      "name": "GitHub",
      "url": "https://github.com/rocketgraphai/xgt_connector",
      "icon": "fa-brands fa-github",
    },
    {
      "name": "PyPI",
      "url": "https://pypi.org/project/xgt_connector",
      "icon": "fa-custom fa-pypi",
    },
    {
      "name": "Rocketgraph",
      "url": "https://rocketgraph.com",
      "icon": "fa-custom fa-rocketgraph",
    },
  ],
}

html_context = {
  # "github_url": "https://github.com", # or your GitHub Enterprise site
  "github_user": "rocketgraphai",
  "github_repo": "xgt_connector",
  "github_version": "main",
  "doc_path": "docs/source",
}

# Left sidebar title
html_title = ""
html_logo = "_static/logo-light.svg"

# Workaround to disable empty sidebars.
html_sidebars = {
  "quick_start": [],
  "requirements": [],
  "RELEASE": [],
  "xgt_connector.Neo4jConnector": [],
  "xgt_connector.Neo4jDriver": [],
}

# Don't execute notebooks when executing.
nb_execution_mode = "off"

# Contents of the sidebar. Since we don't have that many entities that we're
# documenting, we just add the list of everything and a search box.
#
# Technically, this dict maps fileglobs to corresponding sidebar formats.
# Since we want one sidebar for everything, we use the ** to match everything.
#html_sidebars = {
#   '**': ['localtoc.html', 'globaltoc.html', 'relations.html', 'searchbox.html' ]
#}

# Configures the page during generation.
def setup(app):
  # This adds a stylesheet 'link' tag to each page using RELATIVE paths rather
  # than a single fixed path if it was added directly to the 'layout.html' file.
  app.add_css_file('rocketgraph.css')
  # Add special classes for autodocs.
  app.connect("doctree-resolved", add_autodoc_classes)

# Napoleon settings.
# This module enable Sphinx to process NumPy and Google docstrings.
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

def add_autodoc_classes(app, doctree, docname):
  # Add autodoc-section class to sections that are determined to be python api.
  # This is just inferred from the parse tree.
  for node in doctree.traverse():
    if isinstance(node, nodes.section):  # Ensures we only process <section> elements
      # If the first element for a section is py, then it is an autodoc python type.
      for child in node.traverse():
        if (isinstance(child, nodes.Element) and
            child.get("classes") and
            len(child["classes"]) > 0 and
            child["classes"][0] == "py"):
          node["classes"].append("autodoc-section")
