import subprocess
import pathlib


def exec(command):
    """
    Execute bash command

    >>> exec("echo hello")
    'hello'
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return "timeout"

    return result.stdout.rstrip()


def writeFile(filename, content):
    """Write content to filename"""
    pathlib.Path(filename).write_text(content)


def editFile(filename, old, new):
    """
    Replace old with new substring in filename

    >>> editFile('makefile','cucumber','lint')
    '0 replaced'
    >>> editFile('makefile','lint','cucumber')
    '1 replaced'
    >>> editFile('makefile','cucumber','lint')
    '1 replaced'
    """
    content = pathlib.Path(filename).read_text()
    pathlib.Path(filename).write_text(content.replace(old, new))

    return f"{content.count(old)} replaced"


def fetch(url):
    """
    Get url content

    >>> fetch(pathlib.Path("tests/opendsa.html").resolve().as_uri()) # doctest: +ELLIPSIS
    '5.4. Linked Lists — CS3 Data Structures & Algorithms...setNext...'
    >>> fetch(pathlib.Path("tests/neptune.jpg").resolve().as_uri())
    'image/jpeg found'
    """

    from urllib.request import Request, urlopen
    from html import unescape
    from html.parser import HTMLParser
    import re

    class ParagraphExtractor(HTMLParser):
        ignore = ("script", "style", "header", "footer", "form", "nav", "svg")
        blocks = ("section", "div", "p", "li", "dt", "pre", "tr")

        def __init__(self):
            super().__init__()
            self.paras = [""]
            self.ignoring = []
            self.pre = False

        def handle_starttag(self, tag, attrs):
            if tag in self.ignore:
                self.ignoring.append(tag)

            if tag in self.blocks and self.paras[-1]:
                self.paras.append("")

            if tag == "pre":
                self.pre = True

            if tag == "img" and not self.ignoring:
                attrs = dict(attrs)
                if "src" in attrs:
                    self.paras.append(f'![{attrs.get("alt", "")}]({attrs["src"]})')

            if tag in {"h1", "h2", "h3"} and not self.ignoring:
                self.paras.append("#" * int(tag[1]) + " ")

            if tag == "main":
                self.paras = [""]
                self.ignoring = []

        def handle_endtag(self, tag):
            if self.ignoring and self.ignoring[-1] == tag:
                self.ignoring.pop()

            if tag in self.blocks and self.paras[-1]:
                self.paras.append("")

            if tag == "pre":
                self.pre = False

            if tag == "main":
                self.ignoring.append(True)

        def handle_data(self, data):
            data = unescape(data)

            if not self.pre:
                data = data.replace("\n", " ")

            if not self.ignoring:
                if self.paras and self.paras[-1]:
                    self.paras[-1] += " " + data
                else:
                    self.paras.append(data)

        def get_plain(self):
            plain = "\n\n".join([p.rstrip() for p in self.paras if p.strip()])
            plain = re.sub(r"[ \t]+\n", "\n", plain)
            plain = re.sub(r"(?<=\S)[^\S\r\n]{2,}", " ", plain)
            plain = re.sub(r"\n\n\n+", "\n\n", plain)
            return plain.strip()

    request = Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; specialagent)"}
    )

    with urlopen(request, timeout=15) as response:
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
        src = response.read().decode(charset, errors="replace")

    if content_type == "text/plain" or content_type.endswith("json"):
        return src

    if content_type in ("text/html", "application/xhtml+xml"):
        extractor = ParagraphExtractor()
        extractor.feed(src)
        return extractor.get_plain()

    return f"{content_type} found"
