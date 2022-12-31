import os
from typing import List

from dash import dcc
from dash.development.base_component import Component

from shyft.app.controllers._base import _BaseDashController

# TODO: As we will be rewriting the docs in reStructuredText, this won't work anymore. Instead the docs will be
# compiled to HTML and we can display them using an IFrame. Or just serve them statically and link to them.

class MarkdownController(_BaseDashController):

    def page_content(self, fname: str) -> List[Component]:
        with open(os.path.join(self.config.user_docs_dir, f'{fname}.md')) as f:
            markdown = f.read()
        return [
            *self.dc_factory.display_all_messages(),
            dcc.Markdown(markdown),
            self.dc_factory.footer()
        ]