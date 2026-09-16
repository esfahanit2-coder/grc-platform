from io import BytesIO
from urllib.parse import urlparse

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

DEFAULT_CSS = """
@page { size: A4; margin: 18mm; }
body { font-family: 'DejaVu Sans', sans-serif; color: #16243a; font-size: 10pt; line-height: 1.7; }
h1,h2,h3 { color: #10243b; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
th,td { border: 1px solid #d8e1eb; padding: 6px; vertical-align: top; }
th { background: #eef3f8; }
"""


def render_html(template_text, context):
    env=SandboxedEnvironment(undefined=StrictUndefined,autoescape=True)
    env.filters['yesno']=lambda value: 'Yes' if value else 'No'
    template=env.from_string(template_text)
    return template.render(**(context or {}))


def safe_report_url_fetcher(url):
    """Allow only self-contained data URLs in rendered reports.

    Tenant-controlled report templates must not be able to make network
    requests or read local files through WeasyPrint's URL fetcher.
    """
    from weasyprint import default_url_fetcher

    scheme=urlparse(str(url or '')).scheme.lower()
    if scheme=='data':
        return default_url_fetcher(url)
    raise ValueError('External and local resource fetching is disabled for report rendering.')


def render_pdf(template_text, context, css_text=''):
    from weasyprint import CSS, HTML
    html=render_html(template_text,context)
    output=BytesIO()
    HTML(string=html,url_fetcher=safe_report_url_fetcher).write_pdf(
        output,
        stylesheets=[CSS(string=DEFAULT_CSS+'\n'+(css_text or ''),url_fetcher=safe_report_url_fetcher)],
    )
    return output.getvalue(),html
