"""The sidebar's page links: (translation key, page module name) pairs."""
from constants import EXECUTION_VIEW_COUNTRIES

_PAGES = [
    ("nav.overview", "home"),
    ("nav.education", "education"),
    ("nav.health", "health"),
]


def nav_items(country):
    """Links for ``country``; the execution page only where its table exists."""
    items = list(_PAGES)
    if country in EXECUTION_VIEW_COUNTRIES:
        items.append(("nav.execution", "execution"))
    items.append(("nav.about", "about"))
    return items
