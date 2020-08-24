#!/usr/bin/env python3
import os
import os.path
import urllib.request
import urllib.parse
import pathlib
import tinycss2
from bs4 import BeautifulSoup, SoupStrainer
import re
import http.cookiejar
import base64
import sys

class PassthroughHTTPErrorProcessor(urllib.request.HTTPErrorProcessor):
	def http_response(self, request, response):
		return response
	https_response = http_response

class Downloader:
	def __init__(self, source_url_root, target_url_root):
		if not source_url_root.startswith('http://') and not source_url_root.startswith('https://'):
			raise Exception('Source URL root must start with http:// or https://')
		if not target_url_root.startswith('http://') and not target_url_root.startswith('https://'):
			raise Exception('Target URL root must start with http:// or https://')
		self.source_url_root = source_url_root if source_url_root.endswith('/') else source_url_root + '/'
		self.target_url_root = target_url_root if target_url_root.endswith('/') else target_url_root + '/'

		self.cookiejar = http.cookiejar.CookieJar()
		opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookiejar))
		urllib.request.install_opener(opener)

		self.rss_re_pattern = re.compile(re.escape(self.source_url_root) + 'rss(/)?[\'"\\)]{1}')
		self.downloaded_urls = []
		self.target_path_root = pathlib.Path(os.getcwd()) / 'public'
		self.private_site_password = None
		self.rss_override_url = None
		self.auth_header_value = None

	def set_private_mode(self, password, rss_override_url):
		self.private_site_password = password
		self.rss_override_url = rss_override_url if rss_override_url.endswith('/') else rss_override_url + '/'

	def set_basic_auth(self, username, password):
		self.auth_header_value = b'Basic ' + base64.b64encode((username + ':' + password).encode('utf-8'))

	def is_html(self, content_type, normalized_url):
		return content_type == 'text/html' or normalized_url.endswith('.html') or normalized_url.endswith('.htm') or normalized_url.endswith('/')

	def is_xml(self, content_type, normalized_url):
		return content_type == 'text/xml' or content_type == 'application/xml' or normalized_url.endswith('.xml')

	def is_css(self, content_type, normalized_url):
		return content_type == 'text/css' or normalized_url.endswith('.css')

	def is_path_parent(self, parent_path, child_path):
		parent_path = os.path.abspath(parent_path)
		child_path = os.path.abspath(child_path)
		return os.path.commonpath([parent_path]) == os.path.commonpath([parent_path, child_path])

	def normalize_url(self, raw_url):
		url = urllib.parse.urlparse(urllib.parse.urljoin(self.source_url_root, raw_url))
		if url.path == '':
			url = url._replace(path = '/')
		if url.path == '/rss':
			url = url._replace(path = '/rss/')
		return urllib.parse.urlunparse(url)

	def is_port_default(self, url_obj):
		return ((url_obj.scheme == 'http' and (url_obj.port == None or url_obj.port == 80)) or (url_obj.scheme == 'https' and (url_obj.port == None or url_obj.port == 443)))

	def is_url_local(self, url):
		source_parts = urllib.parse.urlparse(self.source_url_root)
		url_parts = urllib.parse.urlparse(url)
		return (source_parts.scheme == url_parts.scheme and source_parts.hostname == url_parts.hostname and (source_parts.port == url_parts.port or self.is_port_default(source_parts) == self.is_port_default(url_parts)))

	def download_url(self, url):
		urlobj = urllib.parse.urlparse(url)
		if urlobj.path == '/rss/' and self.rss_override_url != None:
			url = self.rss_override_url
			print('Overriding RSS URL:', url)
		request = urllib.request.Request(url)
		if self.auth_header_value != None:
			request.add_header('Authorization', self.auth_header_value)
		with urllib.request.urlopen(url) as response:
			return response.info().get_content_type(), response.read()

	def modify_data_simple(self, data):
		doc = data.decode()
		if self.rss_override_url != None:
			doc = doc.replace(self.rss_override_url, self.source_url_root + 'rss/')
		doc = self.rss_re_pattern.sub(self.source_url_root + 'rss.xml', doc)
		doc = doc.replace(self.source_url_root, self.target_url_root)
		alt_source = self.source_url_root.rstrip('/')
		alt_target = self.target_url_root.rstrip('/')
		doc = doc.replace(alt_source, alt_target)
		if '://' in self.source_url_root and '://' in self.target_url_root:
			alt_source = '//' + self.source_url_root.split('://')[1]
			alt_target = '//' + self.target_url_root.split('://')[1]
			doc = doc.replace(alt_source, alt_target)
		data = doc.encode('utf-8')
		return data

	def save_data(self, content_type, norm_url, data):
		path = urllib.parse.urlparse(norm_url).path.lstrip('/')
		if path == '' or path.endswith('/'):
			path += 'index.html'
		if path == 'rss/index.html':
			path = 'rss.xml'
		target_file = self.target_path_root / pathlib.Path(path)
		target_directory = target_file.parent
		if not self.is_path_parent(self.target_path_root, target_file.resolve()):
			raise Exception('Target file is outside global parent!')
		if self.is_html(content_type, norm_url) or self.is_css(content_type, norm_url) or self.is_xml(content_type, norm_url) or path == 'robots.txt':
			data = self.modify_data_simple(data)
		pathlib.Path(target_directory).mkdir(parents=True, exist_ok=True)
		with open(target_file, 'wb') as file:
			file.write(data)

	def get_urls_for_retrieval_from_html(self, data):
		urls = []
		soup = BeautifulSoup(data, features='html.parser')
		for link in soup.findAll('a'):
			if link.has_attr('href'):
				urls.append(self.normalize_url(link['href']))
		for link in soup.findAll('link'):
			if link.has_attr('href'):
				urls.append(self.normalize_url(link['href']))
		for link in soup.findAll('img'):
			if link.has_attr('src'):
				urls.append(self.normalize_url(link['src']))
		for link in soup.findAll('script'):
			if link.has_attr('src'):
				urls.append(self.normalize_url(link['src']))
		for style in soup.findAll('style'):
			urls = urls + self.get_urls_for_retrieval_from_css(style.string.encode('utf-8'))
		return urls

	def get_urls_for_retrieval_from_xml(self, data):
		urls = []
		soup = BeautifulSoup(data, features='html.parser')
		for link in soup.findAll('loc'):
			urls.append(self.normalize_url(link.text))
		return urls

	def check_css_for_urls(self, components):
		if components is None:
			return []
		urls = []
		for component in components:
			if component.type == 'url' and not component.value.startswith('data:'):
				urls.append(self.normalize_url(component.value))
			if hasattr(component, 'content'):
				urls = urls + self.check_css_for_urls(component.content)
		return urls

	def get_urls_for_retrieval_from_css(self, data):
		urls = []
		css_rules, css_encoding = tinycss2.parse_stylesheet_bytes(data, skip_comments=True, skip_whitespace=True)
		for rule in css_rules:
			urls = urls + self.check_css_for_urls(rule.prelude)
			urls = urls + self.check_css_for_urls(rule.content)
		return urls

	def retrieve_all(self, url):
		norm_url = self.normalize_url(url)
		if norm_url in self.downloaded_urls:
			return
		if not self.is_url_local(norm_url):
			return
		print(norm_url)
		self.downloaded_urls.append(norm_url)

		try:
			content_type, data = self.download_url(norm_url)
		except Exception as e:
			print('WARNING: unable to download "' + url + '": ' + str(e))
			return

		self.save_data(content_type, norm_url, data)

		if self.is_html(content_type, norm_url):
			for link in self.get_urls_for_retrieval_from_html(data):
				self.retrieve_all(link)
		if self.is_xml(content_type, norm_url):
			for link in self.get_urls_for_retrieval_from_xml(data):
				self.retrieve_all(link)
		if self.is_css(content_type, norm_url):
			for link in self.get_urls_for_retrieval_from_css(data):
				self.retrieve_all(link)

	def go(self):
		if self.private_site_password != None:
			payload = {
				'r': '/',
				'password': self.private_site_password
			}
			request = urllib.request.Request(self.source_url_root + 'private/', urllib.parse.urlencode(payload).encode('utf-8'))
			if self.auth_header_value != None:
				request.add_header('Authorization', self.auth_header_value)
			opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookiejar), PassthroughHTTPErrorProcessor)
			with opener.open(request) as response:
				if response.status != 302:
					raise Exception('Failed to authenticate in private mode!')
		
		self.retrieve_all(self.source_url_root + 'sitemap.xml')
		self.retrieve_all(self.source_url_root + 'robots.txt')
		self.retrieve_all(self.source_url_root + 'favicon.ico')


source_url = os.getenv('ECTO1_SOURCE')
target_url = os.getenv('ECTO1_TARGET')
private_password = os.getenv('ECTO1_PRIVATE_PASSWORD')
private_rss_url = os.getenv('ECTO1_PRIVATE_RSS_URL')
basic_auth_username = os.getenv('ECTO1_BASIC_AUTH_USERNAME', '')
basic_auth_password = os.getenv('ECTO1_BASIC_AUTH_PASSWORD', '')

if source_url == None or target_url == None:
	print('ecto1.py: the Ghost blog downloader/scraper/static-site-maker')
	print('See https://github.com/arktronic/ecto1 for license info, etc.')
	print('')
	print('Usage is all based on setting environment variables:')
	print('ECTO1_SOURCE=http://internal-url.example.net ECTO1_TARGET=https://public-url.example.com python3 etco1.py')
	print('')
	print('If the Ghost site is in private mode, specify the password and the private RSS link:')
	print('ECTO1_PRIVATE_PASSWORD=abcd1234 ECTO1_PRIVATE_RSS_URL=http://internal-url.example.net/acbacbacbacbabcbabcbacabb/rss ...')
	print('')
	print('If the Ghost site is behind a basic auth reverse proxy, specify the username and/or password:')
	print('ECTO1_BASIC_AUTH_USERNAME=user ECTO1_BASIC_AUTH_PASSWORD=pass ...')
	print('')
	print('IMPORTANT: It is assumed that you own the rights to the Ghost site being downloaded. No throttling is implemented.')
	sys.exit(1)

d = Downloader(source_url, target_url)
print('ecto1.py')

if private_password != None and private_rss_url != None:
	d.set_private_mode(private_password, private_rss_url)
	print('Private mode: ON')
else:
	print('Private mode: OFF')

if basic_auth_username != '' or basic_auth_password != '':
	d.set_basic_auth(basic_auth_username, basic_auth_password)
	print('Basic auth: ON')
else:
	print('Basic auth: OFF')

d.go()

print('Done. Contents have been downloaded into:', pathlib.Path(os.getcwd()) / 'public')
