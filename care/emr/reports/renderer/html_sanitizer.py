"""Keep HTML reports passive, including when inserted into a preview's Shadow DOM."""

from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

import tinycss2
import tinyhtml5

REPORT_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; img-src data:; font-src data:; "
    "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)

_ALLOWED_TAGS = frozenset(
    [
        "html",
        "head",
        "body",
        "title",
        "style",
        "div",
        "center",
        "span",
        "font",
        "p",
        "label",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "caption",
        "colgroup",
        "col",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "s",
        "mark",
        "del",
        "ins",
        "small",
        "sub",
        "sup",
        "br",
        "hr",
        "a",
        "img",
        "pre",
        "code",
        "kbd",
        "blockquote",
        "q",
        "cite",
        "dl",
        "dt",
        "dd",
        "section",
        "nav",
        "aside",
        "header",
        "footer",
        "main",
        "article",
        "figure",
        "figcaption",
        "address",
        "abbr",
        "time",
    ]
)
_COMMON_ATTRIBUTES = frozenset({"class", "id", "title", "lang", "dir", "style"})
_TAG_ATTRIBUTES = {
    "a": {"href"},
    "img": {"src", "alt", "width", "height"},
    "col": {"span", "width"},
    "colgroup": {"span", "width"},
    "table": {"width", "cellpadding", "cellspacing", "border"},
    "td": {"colspan", "rowspan", "headers", "width", "height"},
    "th": {"colspan", "rowspan", "headers", "scope", "width", "height"},
    "ol": {"start", "reversed", "type"},
    "li": {"value"},
    "time": {"datetime"},
}
_IMAGE_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/webp", "image/avif", "image/bmp"}
)
# CSS functions are opt-in: url(), image-set(), and escaped variants cannot load
# resources. Strings containing URLs are also inert without those functions.
_CSS_FUNCTIONS = frozenset(
    "rgb rgba hsl hsla hwb lab lch oklab oklch color color-mix "
    "calc min max clamp var env counter counters "
    "linear-gradient radial-gradient conic-gradient "
    "repeating-linear-gradient repeating-radial-gradient repeating-conic-gradient "
    "repeat minmax fit-content cubic-bezier steps "
    "translate translateX translateY translateZ translate3d "
    "scale scaleX scaleY scaleZ scale3d rotate rotateX rotateY rotateZ rotate3d "
    "skew skewX skewY matrix matrix3d perspective "
    "not is where has nth-child nth-last-child nth-of-type nth-last-of-type lang dir".lower().split()
)
_CSS_RULES = frozenset(
    [
        "media",
        "supports",
        "page",
        "layer",
        "container",
        "font-face",
        "keyframes",
        "top-left-corner",
        "top-left",
        "top-center",
        "top-right",
        "top-right-corner",
        "bottom-left-corner",
        "bottom-left",
        "bottom-center",
        "bottom-right",
        "bottom-right-corner",
        "left-top",
        "left-middle",
        "left-bottom",
        "right-top",
        "right-middle",
        "right-bottom",
    ]
)


def _safe_css_tokens(tokens):
    for token in tokens:
        if token.type in {"url", "error"}:
            return False
        if token.type == "function" and (
            token.lower_name not in _CSS_FUNCTIONS
            or not _safe_css_tokens(token.arguments)
        ):
            return False
        if hasattr(token, "content") and not _safe_css_tokens(token.content):
            return False
    return True


def _sanitize_css(css, *, inline=False):
    parser = (
        tinycss2.parse_declaration_list if inline else tinycss2.parse_blocks_contents
    )
    rules = parser(css, skip_comments=True, skip_whitespace=True)
    clean = []
    for rule in rules:
        if rule.type == "declaration":
            if _safe_css_tokens(rule.value):
                clean.append(rule.serialize() + ";")
        elif rule.type == "qualified-rule" and not inline:
            if _safe_css_tokens(rule.prelude):
                clean.append(
                    tinycss2.serialize(rule.prelude)
                    + "{"
                    + _sanitize_css(rule.content)
                    + "}"
                )
        elif (
            rule.type == "at-rule"
            and not inline
            and rule.lower_at_keyword in _CSS_RULES
            and rule.content is not None
            and _safe_css_tokens(rule.prelude)
        ):
            clean.append(
                "@"
                + rule.lower_at_keyword
                + " "
                + tinycss2.serialize(rule.prelude)
                + "{"
                + _sanitize_css(rule.content)
                + "}"
            )
    # HTML serialization leaves style text unescaped. Prevent a CSS string from
    # becoming an HTML end tag when this document is parsed again by a browser.
    return "".join(clean).replace("<", "\\3c ")


def _is_inline_image(url):
    media_type, separator, _ = url.partition(",")
    return (
        bool(separator)
        and media_type.lower().startswith("data:")
        and media_type[5:].split(";", 1)[0].lower() in _IMAGE_TYPES
    )


def _is_safe_link(url):
    if any(ord(char) < 32 or ord(char) == 127 for char in url):  # noqa: PLR2004
        return False
    try:
        return url.startswith("#") or urlsplit(url).scheme.lower() in {
            "https",
            "http",
            "mailto",
            "tel",
        }
    except ValueError:
        return False


def _sanitize_element(element):
    for child in list(element):
        if child.tag not in _ALLOWED_TAGS:
            # Drop active/foreign content entirely. Preserve following report text.
            if child.tail:
                index = list(element).index(child)
                if index:
                    previous = element[index - 1]
                    previous.tail = (previous.tail or "") + child.tail
                else:
                    element.text = (element.text or "") + child.tail
            element.remove(child)
            continue
        _sanitize_element(child)

    allowed_attributes = _COMMON_ATTRIBUTES | _TAG_ATTRIBUTES.get(element.tag, set())
    for name, value in list(element.attrib.items()):
        if name not in allowed_attributes:
            del element.attrib[name]
        elif name == "style":
            element.attrib[name] = _sanitize_css(value, inline=True)
        elif (name == "src" and not _is_inline_image(value)) or (
            name == "href" and not _is_safe_link(value)
        ):
            del element.attrib[name]

    if element.tag == "style":
        element.text = _sanitize_css(element.text or "")


def sanitize_report_html(html: str) -> str:
    # Parse using the HTML5 tree rules used by browsers, rather than trying to
    # match resource attributes or malformed/foreign markup with regular expressions.
    root = tinyhtml5.parse(html, namespace_html_elements=False)
    _sanitize_element(root)
    head = root.find("head")
    head.insert(0, ET.Element("meta", {"charset": "utf-8"}))
    head.insert(
        1,
        ET.Element(
            "meta",
            {
                "http-equiv": "Content-Security-Policy",
                "content": REPORT_CONTENT_SECURITY_POLICY,
            },
        ),
    )
    return "<!DOCTYPE html>\n" + ET.tostring(root, encoding="unicode", method="html")
