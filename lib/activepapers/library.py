import json
import os
from activepapers import url

#
# The ACTIVEPAPERS_LIBRARY environment variable follows the
# same conventions as PATH under Unix.
#
library = os.environ.get('ACTIVEPAPERS_LIBRARY', None)
if library is None:
    # This is Unix-only, needs a Windows equivalent
    home = os.environ.get('HOME', None)
    if home is not None:
        library = os.path.join(home, '.activepapers')
        if not os.path.exists(library):
            try:
                os.mkdir(library)
            except IOError:
                library = None

library = library.split(':')

def split_paper_ref(paper_ref):
    index = paper_ref.find(':')
    if index == -1:
        raise ValueError("invalid paper reference %s" % paper_ref)
    return paper_ref[:index].lower(), paper_ref[index+1:]


#
# Return the local filename for a paper reference,
# after downloading the file if required.
#

def _get_local_file(label):
    filename = label + '.ap'
    for dir in library:
        full_name = os.path.join(dir, "local", filename)
        if os.path.exists(full_name):
            return full_name
    raise IOError(2, "No such ActivePaper: 'local:%s' (filename: %s)"
                  % (label, full_name))

def _get_figshare_doi(label, local_filename):
    figshare_url = "http://api.figshare.com/v1/articles/%s" % label
    try:
        response = url.urlopen(figshare_url)
        json_data = response.read().decode("utf-8")
    except url.HTTPError:
        raise ValueError("Not a figshare DOI: %s" % label)
    article_details = json.loads(json_data)
    download_url = article_details['items'][0]['files'][0]['download_url']
    url.urlretrieve(download_url, local_filename)
    return local_filename

def _get_zenodo_doi(label, local_filename):
    try:
        # Python 2
        from HTMLParser import HTMLParser
        bytes2text = lambda x: x
    except ImportError:
        # Python 3
        from html.parser import HTMLParser
        def bytes2text(b):
            return b.decode(encoding="utf8")
    class ZenodoParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "link":
                attrs = dict(attrs)
                if attrs.get("rel") == "alternate" \
                   and attrs.get("type") != "application/rss+xml":
                    self.link_href = attrs.get("href")
                    self.link_type = attrs.get("type")

    zenodo_url = "http://dx.doi.org/" + label
    parser = ZenodoParser()
    source = url.urlopen(zenodo_url)
    try:
        parser.feed(bytes2text(source.read()))
    finally:
        source.close()
    assert parser.link_type == "application/octet-stream"
    download_url = parser.link_href
    url.urlretrieve(download_url, local_filename)
    return local_filename

def _get_doi(label):
    local_filename = os.path.join(library[0], label + ".ap")
    if os.path.exists(local_filename):
        return local_filename

    dir_name = os.path.join(library[0], label.split("/")[0])
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    # There doesn't seem to be a way to download an
    # arbitrary digital object through its DOI. We know
    # know how to do it for figshare and Zenodo, which are
    # each handled by specialized code.

    # Figshare
    if 'figshare' in label:
        return _get_figshare_doi(label, local_filename)
    # Zenodo
    elif 'zenodo' in label:
        return _get_zenodo_doi(label, local_filename)
    # Nothing else works for now
    else:
        raise ValueError("Unrecognized DOI: %s" % label)


download_handlers = {'local': _get_local_file,
                     'doi': _get_doi}

def find_in_library(paper_ref):
    ref_type, label = split_paper_ref(paper_ref)
    handler = download_handlers.get(ref_type)
    assert handler is not None
    return handler(label)
