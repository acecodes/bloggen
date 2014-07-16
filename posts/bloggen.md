title: Bloggen
date: 2014-07-02
published: true

## Bloggen
#### Create static HTML/CSS blogs with Flask
----------

Hello, this is a sample Markdown file that can act as a guide for how to format blog posts. The <code>title</code>, <code>date</code> and <code>published</code> YAML variables at the top of this file (not visible to anyone viewing the HTML version of this), act just as their names imply. It is important to note that if <code>published</code> is either absent or set to <code>false</code>, then this post will not appear in the main index page.

Bloggen also offers syntax highlighting via the Pygments library. Here's an example of how to format it (again, only the end result is visible to those viewing the HTML version of this):

	:::python
	from urlparse import urljoin
	from flask import request
	from werkzeug.contrib.atom import AtomFeed


	def make_external(url):
	    return urljoin(request.url_root, url)


	@app.route('/recent.atom')
	def recent_feed():
	    feed = AtomFeed('Recent Articles',
	                    feed_url=request.url, url=request.url_root)
	    articles = Article.query.order_by(Article.pub_date.desc()) \
	                      .limit(15).all()
	    for article in articles:
	        feed.add(article.title, unicode(article.rendered_text),
	                 content_type='html',
	                 author=article.author.name,
	                 url=make_external(article.url),
	                 updated=article.last_update,
	                 published=article.published)
	    return feed.get_response()
	    
Brought to you by [acecodes.net][1].


  [1]: http://www.acecodes.net