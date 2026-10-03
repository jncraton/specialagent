import subprocess
import pathlib


def exec(command):
    """
    Execute bash command

    >>> exec("echo hello")
    'hello'
    """

    return subprocess.getoutput(command)


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
    Get content from url

    >>> fetch(pathlib.Path("tests/opendsa.html").resolve().as_uri()) # doctest: +ELLIPSIS
    '5.4. Linked Lists — CS3 Data Structures & Algorithms...setNext...'
    """

    from urllib.request import Request, urlopen
    from html import unescape
    from html.parser import HTMLParser
    import re

    class ParagraphExtractor(HTMLParser):
        paras = [""]
        ignoring = []
        pre = False
        ignore = ("script", "style", "header", "footer", "form", "nav", "svg")
        blocks = ("section", "div", "p", "li", "dt", "pre", "tr")

        def handle_starttag(self, tag, attrs):
            if tag in self.ignore:
                self.ignoring.append(tag)

            if tag in self.blocks and self.paras[-1]:
                self.paras.append("")

            if tag == "pre":
                self.pre = True

        def handle_endtag(self, tag):
            if self.ignoring and self.ignoring[-1] == tag:
                self.ignoring.pop()

            if tag in self.blocks and self.paras[-1]:
                self.paras.append("")

            if tag == "pre":
                self.pre = False

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
        src = response.read().decode("utf-8", errors="replace")

    extractor = ParagraphExtractor()
    extractor.feed(src)
    return extractor.get_plain()
