"""SEO helpers: canonical URLs, absolute asset URLs, and structured data.

All public-facing URLs are generated against ``SITE_URL`` (the production
domain) rather than the incoming request host, so canonical/OG/sitemap
URLs never leak ``localhost`` even when running locally or behind a proxy.
"""

from flask import current_app, request, url_for

DEFAULT_OG_IMAGE_PATH = "img/iruri-logo.png"


def site_url():
    return current_app.config.get("SITE_URL", "https://iruriproperties.online").rstrip(
        "/"
    )


def absolute_static_url(filename):
    return f"{site_url()}{url_for('static', filename=filename)}"


def default_og_image():
    return absolute_static_url(DEFAULT_OG_IMAGE_PATH)


def canonical_url(path=None):
    path = path if path is not None else request.path
    return f"{site_url()}{path}"


def absolute_url_for(endpoint, **values):
    return f"{site_url()}{url_for(endpoint, **values)}"
