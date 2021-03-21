import os
from typing import List

import dash_core_components as dcc
from dash.development.base_component import Component

from shyft.dash_app.view.controller._base import _BaseController


class MarkdownController(_BaseController):

    def page_content(self, fname: str) -> List[Component]:
        with open(os.path.join(self.config.user_docs_dir, f'{fname}.md')) as f:
            markdown = f.read()
        return [
            *self.dc_factory.display_all_messages(),
            dcc.Markdown(markdown),
            self.dc_factory.footer()
        ]