from flask import Flask, render_template, url_for, abort, request
from flask.ext.frozen import Freezer
from werkzeug import cached_property
from werkzeug.contrib.atom import AtomFeed
from boto.s3.key import Key
import sys
import markdown
import os
import yaml
import collections
import boto
import aws_settings


# Configuration settings
POSTS_FILE_EXTENSION = '.md'
FREEZER_BASE_URL = 'http://testing123.com'  # CHANGE THIS!
author = "Buzz Killington"  # CHANGE THIS!

# Custom dictionary class that sorts items by date


class SortedDict(collections.MutableMapping):

    def __init__(self, items=None, key=None, reverse=False):
        self._items = {}
        self._keys = []
        if key:
            self._key_fn = lambda k: key(self._items[k])
        else:
            self._key_fn = lambda k: self._items[k]
        self._reverse = reverse

        if items is not None:
            self.update(items)

    def __getitem__(self, key):
        return self._items[key]

    def __setitem__(self, key, value):
        self._items[key] = value
        if key not in self._keys:
            self._keys.append(key)
            self._keys.sort(key=self._key_fn, reverse=self._reverse)

    def __delitem__(self):
        self._items.pop(key)
        self._keys.remove(key)

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        for key in self._keys:
            yield key

    def __repr__(self):
        return '{0}({1})'.format(self.__class__.__name__, self._items)

# Class for handling the blog itself that creates an API for accessing posts


class Blog(object):

    def __init__(self, app, root_dir='', file_ext=None):
        self.root_dir = root_dir
        self.file_ext = file_ext if file_ext is not None else app.config[
            'POSTS_FILE_EXTENSION']
        self._app = app
        self._cache = SortedDict(key=lambda p: p.date, reverse=True)
        self._initialize_cache()

    @property
    def posts(self):
        if self._app.debug:
            return self._cache.values()
        else:
            return [post for post in self._cache.values() if post.published]

    def get_post_or_404(self, path):
        """Returns the post object for the given path or raises a NotFound exception"""
        try:
            return self._cache[path]
        except KeyError:
            abort(404)

    def _initialize_cache(self):
        """Walks the root directory and adds all posts to the cache"""
        for (root, dirpaths, filepaths) in os.walk(self.root_dir):
            for filepath in filepaths:
                filename, ext = os.path.splitext(filepath)
                if ext == self.file_ext:
                    path = os.path.join(root, filepath).replace(self.root_dir, '')
                    post = Post(path, root_dir=self.root_dir)
                    self._cache[post.urlpath] = post

# Class that converts Markdown files into posts


class Post(object):

    def __init__(self, path, root_dir=''):
        self.urlpath = os.path.splitext(path.strip('/'))[0]
        self.filepath = os.path.join(root_dir, path.strip('/'))
        # Keeps post in draft mode, must be changed in original Markup file in
        # order for post to be published to main feed
        self.published = False
        self._initialize_metadata()

    @cached_property
    def html(self):
        with open(self.filepath, 'r') as file_input:
            content = file_input.read().split('\n\n', 1)[1].strip()

        # Codehilite highlights syntax
        return markdown.markdown(content, extensions=['codehilite'])

    def url(self, _external=False):
        return url_for('post', path=self.urlpath, _external=_external)

    def _initialize_metadata(self):
        content = ''
        with open(self.filepath, 'r') as file_input:
            for line in file_input:
                if not line.strip():
                    break
                content += line

        self.__dict__.update(yaml.load(content))

app = Flask(__name__)
app.config.from_object(__name__)
blog = Blog(app, root_dir='posts')
freezer = Freezer(app)


@app.template_filter('date')
def format_date(value, format='%B %d, %Y'):
    return value.strftime(format)


@app.route('/')
def index():
    return render_template('index.html', posts=blog.posts)


@app.route('/blog/<path:path>/')
def post(path):
    post = blog.get_post_or_404(path)
    return render_template('post.html', post=post)


@app.route('/feed.atom')
def feed():
    feed = AtomFeed('Recent Articles', feed_url=request.url, url=request.url_root)
    posts = blog.posts
    title = lambda p: '%s: %s' % (p.title, p.subtitle) if hasattr(p, 'subtitle') else p.title

    for post in posts:
        feed.add(title(post),
                 post.html,
                 content_type='html',
                 author=author,
                 url=post.url(_external=True),
                 updated=post.date,
                 published=post.date)

    return feed.get_response()


def deploy(root_dir):
    conn = boto.connect_s3(aws_settings.AWS_ACCESS_KEY_ID, aws_settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(aws_settings.DOMAIN)
    for (root, dirpaths, filepaths) in os.walk(root_dir):
        for filepath in filepaths:
            filename = os.path.join(root, filepath)
            name = filename.replace(root_dir, '', 1)[1:]
            key = Key(bucket, name)
            key.set_contents_from_filename(filename)

    print('Site is now up on {site}'.format(site=bucket.get_website_endpoint()))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'build':
        freezer.freeze()
    elif len(sys.argv) > 1 and sys.argv[1] == 'deploy':
        freezer.freeze()
        deploy('build')
    else:
        post_files = [post.filepath for post in blog.posts]
        app.run(port=8000, debug=True, extra_files=post_files)
