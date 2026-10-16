"""The sidebar's page links: (translation key, page module name) pairs."""
from constants import AGRICULTURE_VIEW_COUNTRIES, EXECUTION_VIEW_COUNTRIES

_PAGES = [
    ("nav.overview", "home"),
    ("nav.education", "education"),
    ("nav.health", "health"),
]


def nav_items(country):
    """Links for ``country``; the execution and agriculture pages only where
    their data exist."""
    items = list(_PAGES)
    if country in AGRICULTURE_VIEW_COUNTRIES:
        items.append(("nav.agriculture", "agriculture"))
    if country in EXECUTION_VIEW_COUNTRIES:
        items.append(("nav.execution", "execution"))
    items.append(("nav.about", "about"))
    return items
