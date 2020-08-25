# ecto1
A downloader/scraper/static-site-maker for [Ghost](https://github.com/TryGhost/Ghost) blogs

## Why?
Because I wanted a way to have a nice, modern WYSIWYG blog editing experience combined with the speed and security of a static website. (And I wanted to keep the Ghost themes intact instead of re-implementing them in a static site generator - so the Content API is not used.)

## How do I use it?
With Python 3 and environment variables.

Here's the help text from the script:
```
ecto1.py: the Ghost blog downloader/scraper/static-site-maker
See https://github.com/arktronic/ecto1 for license info, etc.

Usage is all based on setting environment variables:
ECTO1_SOURCE=http://internal-url.example.net ECTO1_TARGET=https://public-url.example.com python3 etco1.py

If the Ghost site is in private mode, specify the password and the private RSS link:
ECTO1_PRIVATE_PASSWORD=abcd1234 ECTO1_PRIVATE_RSS_URL=http://internal-url.example.net/acbacbacbacbabcbabcbacabb/rss ...

If the Ghost site is behind a pre-authentication gateway, specify its POST URL and Base64-encoded POST data:
ECTO1_PRE_AUTH_URL=http://authentication.example.net/login ECTO1_PRE_AUTH_POST_DATA="dXNlcm5hbWU9aGVsbG8mcGFzc3dvcmQ9d29ybGQ=" ...

IMPORTANT: It is assumed that you own the rights to the Ghost site being downloaded. No throttling is implemented.
```

Don't forget to run `pip install -r requirements.txt` first.
