"""Enlaces <head> compartidos para ebooks Liviin."""

FONT_LINK = (
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond'
    ':ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500'
    '&family=Cormorant+SC:wght@300;400;500'
    '&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">'
)
EBOOK_CSS_LINK = '<link rel="stylesheet" href="css/ebook.css">'


def ebook_head_links() -> str:
    return f"{FONT_LINK}\n{EBOOK_CSS_LINK}"
