import json
from datetime import date
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

from books.models import Book, BookGenre, Genre


ALADIN_ITEM_SEARCH_URL = 'https://www.aladin.co.kr/ttb/api/ItemSearch.aspx'
ALADIN_CATEGORY_MAP = {
    '소설/시/희곡': '소설/시/희곡',
    '에세이': '소설/시/희곡',
    '경제경영': '경제/경영',
    '경제/경영': '경제/경영',
    '자기계발': '자기계발',
    '인문학': '인문/교양',
    '인문/교양': '인문/교양',
    '과학': '과학',
    '어린이': '어린이/청소년',
    '청소년': '어린이/청소년',
    '예술/대중문화': '예술/대중문화',
    '건강/취미': '취미/실용',
    '가정/요리/뷰티': '취미/실용',
    '여행': '취미/실용',
    '수험서/자격증': '취미/실용',
    '외국어': '외국어/외국도서',
    '외국도서': '외국어/외국도서',
    '만화/라이트노벨': '만화/라이트노벨',
}


def search_books_preview(query, max_results=20):
    from django.core.cache import cache
    cache_key = f'aladin_preview:{query}:{max_results}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    items = _search_aladin(query, max_results=max_results)
    result = [_item_to_preview(item) for item in items if item.get('isbn13') or item.get('isbn')]
    cache.set(cache_key, result, timeout=900)
    return result


def materialize_book(payload):
    isbn = (payload.get('isbn') or '').strip()
    if not isbn:
        raise ValueError('isbn 필수')
    book, _ = Book.objects.update_or_create(
        isbn=isbn,
        defaults={
            'title': payload.get('title', ''),
            'author': payload.get('author', ''),
            'publisher': payload.get('publisher', ''),
            'description': payload.get('description', ''),
            'cover_image': payload.get('cover_image', ''),
            'published_date': _parse_pub_date(payload.get('published_date')),
        },
    )
    for genre_data in payload.get('genres', []):
        genre_name = (genre_data.get('name') or '').strip()
        if genre_name:
            genre = Genre.objects.filter(name=genre_name).first()
            if genre:
                BookGenre.objects.get_or_create(book=book, genre=genre)
    return book


def search_and_save_books(query, max_results=10):
    items = _search_aladin(query, max_results=max_results)
    return _save_books(items)


def _item_to_preview(item):
    isbn = item.get('isbn13') or item.get('isbn', '')
    genre_name = _resolve_genre_name(item.get('categoryName', ''))
    return {
        'id': None,
        'isbn': isbn,
        'title': item.get('title', ''),
        'author': item.get('author', ''),
        'publisher': item.get('publisher', ''),
        'description': item.get('description', ''),
        'cover_image': item.get('cover', ''),
        'published_date': str(_parse_pub_date(item.get('pubDate'))),
        'average_rating': '0.0',
        'genres': [{'id': None, 'name': genre_name}] if genre_name else [],
        'is_wishlisted': False,
        'is_collected': False,
    }


def _resolve_genre_name(category_name):
    parts = [p.strip() for p in category_name.split('>') if p.strip()]
    if not parts:
        return ''
    aladin_category = parts[1] if len(parts) > 1 else parts[0]
    return ALADIN_CATEGORY_MAP.get(aladin_category, '')


def _search_aladin(query, max_results=10):
    if not settings.ALADIN_TTB_KEY:
        return []

    params = {
        'ttbkey': settings.ALADIN_TTB_KEY,
        'Query': query,
        'QueryType': 'Keyword',
        'MaxResults': max_results,
        'Start': 1,
        'SearchTarget': 'Book',
        'Output': 'JS',
        'Version': '20131101',
    }
    url = f'{ALADIN_ITEM_SEARCH_URL}?{urlencode(params)}'

    try:
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return []

    return data.get('item', [])


def _save_books(items):
    books = []
    for item in items:
        isbn = item.get('isbn13') or item.get('isbn')
        if not isbn:
            continue

        book, _ = Book.objects.update_or_create(
            isbn=isbn,
            defaults={
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'publisher': item.get('publisher', ''),
                'description': item.get('description', ''),
                'cover_image': item.get('cover', ''),
                'published_date': _parse_pub_date(item.get('pubDate')),
            },
        )
        _link_genre(book, item.get('categoryName', ''))
        books.append(book)

    return books


def _parse_pub_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


def _link_genre(book, category_name):
    parts = [p.strip() for p in category_name.split('>') if p.strip()]
    if not parts:
        return

    aladin_category = parts[1] if len(parts) > 1 else parts[0]
    genre_name = ALADIN_CATEGORY_MAP.get(aladin_category, '')
    if not genre_name:
        return

    genre = Genre.objects.filter(name=genre_name).first()
    if genre:
        BookGenre.objects.get_or_create(book=book, genre=genre)
