from flask import Flask, render_template
from werkzeug import cached_property
import markdown
import os
import yaml

POSTS_FILE_EXTENSION = '.md'
app = Flask(__name__)

class Post(object):
	def __init__(self, path):
		self.path = path

	@cached_property
	def html(self):
		with open(self.path, 'r') as file_input:
			content = file_input.read().strip()

		return markdown.markdown(content)

	def _initialize_metadata(self):
		content = ''
		with open(self.path, 'r') as file_input:
			for line in file_input:
				if not line.strip():
					break
				content += line

		self.__dict__.update(yaml.load(content))

@app.route('/')
def index():
	return 'Hello, world!'

@app.route('/blog/<path:path>')
def post(path):
	path = os.path.join('posts', path + POSTS_FILE_EXTENSION)
	post = Post(path)
	return render_template('post.html', post=post)

if __name__ == '__main__':
	app.run(debug=True, port=8000)