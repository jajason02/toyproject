from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Book, Collection, Genre, Review, ReviewLike, Wishlist
from .serializers import (
    BookDetailSerializer,
    BookListSerializer,
    FeedReviewSerializer,
    ReviewSerializer,
    WishlistSerializer,
    GenreSerializer,
)
from .services.aladin import materialize_book, search_books_preview


@require_GET
def book_cover(request, book_pk):
    book = Book.objects.filter(pk=book_pk).only('cover_image').first()
    if book is None:
        return JsonResponse(
            {'error': '도서를 찾을 수 없습니다.'},
            status=404,
        )

    try:
        cover_request = UrlRequest(
            book.cover_image,
            headers={'User-Agent': 'ArcticBookService/1.0'},
        )
        with urlopen(cover_request, timeout=5) as cover_response:
            content_type = cover_response.headers.get_content_type()
            cover_content = cover_response.read(5 * 1024 * 1024 + 1)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return JsonResponse(
            {'error': '도서 표지를 불러오지 못했습니다.'},
            status=502,
        )

    if not content_type.startswith('image/'):
        return JsonResponse(
            {'error': '표지 주소가 이미지가 아닙니다.'},
            status=502,
        )
    if len(cover_content) > 5 * 1024 * 1024:
        return JsonResponse(
            {'error': '도서 표지 파일이 너무 큽니다.'},
            status=502,
        )

    response = HttpResponse(
        cover_content,
        content_type=content_type,
    )
    response['Cache-Control'] = 'public, max-age=86400'
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def genre_list(request):
    genres = Genre.objects.order_by('id')
    serializer = GenreSerializer(genres, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def book_list(request):
    paginator = PageNumberPagination()
    paginator.page_size = 12

    books = Book.objects.prefetch_related('genres')

    search = request.query_params.get('search', '').strip()
    if search:
        books = books.filter(
            Q(title__icontains=search) | Q(author__icontains=search),
        )
        if not books.exists() and not request.query_params.get('genre'):
            preview_books = search_books_preview(search)
            if preview_books:
                page = paginator.paginate_queryset(preview_books, request)
                return paginator.get_paginated_response(page)

    genre_id = request.query_params.get('genre')
    if genre_id:
        if not genre_id.isdigit():
            return Response(
                {'error': 'genre는 장르 ID여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        books = books.filter(genres__id=genre_id)

    ordering = request.query_params.get('ordering', 'latest')
    if ordering == 'rating':
        books = books.order_by('-average_rating', '-published_date', '-id')
    elif ordering == 'latest':
        books = books.order_by('-published_date', '-id')
    else:
        return Response(
            {'error': 'ordering은 rating 또는 latest만 사용할 수 있습니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    page = paginator.paginate_queryset(books, request)
    serializer = BookListSerializer(page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def book_detail(request, book_pk):
    books = Book.objects.prefetch_related('genres', 'reviews__user')
    book = books.filter(pk=book_pk).first()
    if book is None:
        return Response(
            {'error': '도서를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = BookDetailSerializer(book, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def popular_book_list(request):
    books = Book.objects.prefetch_related('genres').order_by(
        '-average_rating',
        '-published_date',
        '-id',
    )[:10]
    serializer = BookListSerializer(books, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def following_review_feed(request):
    following_user_ids = request.user.followings.values_list(
        'to_user_id',
        flat=True,
    )
    reviews = Review.objects.filter(
        user_id__in=following_user_ids,
    ).select_related(
        'user',
        'book',
    ).prefetch_related(
        'likes',
        'book__genres',
    ).order_by(
        '-created_at',
        '-id',
    )
    serializer = FeedReviewSerializer(
        reviews,
        many=True,
        context={'request': request},
    )
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review_create(request, book_pk):
    book = Book.objects.filter(pk=book_pk).first()
    if book is None:
        return Response(
            {'error': '도서를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if Review.objects.filter(user=request.user, book=book).exists():
        return Response(
            {'error': '이미 이 도서에 리뷰를 작성했습니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ReviewSerializer(
        data=request.data,
        context={'request': request},
    )
    if serializer.is_valid():
        serializer.save(user=request.user, book=book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def review_update_delete(request, book_pk, review_pk):
    review = Review.objects.filter(pk=review_pk, book_id=book_pk).first()
    if review is None:
        return Response(
            {'error': '리뷰를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if review.user != request.user:
        return Response(
            {'error': '본인의 리뷰만 수정하거나 삭제할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'DELETE':
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ReviewSerializer(
        review,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request},
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review_like_toggle(request, review_pk):
    review = Review.objects.filter(pk=review_pk).first()
    if review is None:
        return Response(
            {'error': '리뷰를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    like, is_created = ReviewLike.objects.get_or_create(
        user=request.user,
        review=review,
    )
    if not is_created:
        like.delete()

    return Response(
        {
            'is_liked': is_created,
            'like_count': review.likes.count(),
        },
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wishlist_toggle(request, book_pk):
    book = Book.objects.filter(pk=book_pk).first()
    if book is None:
        return Response(
            {'error': '도서를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    wishlist, is_created = Wishlist.objects.get_or_create(
        user=request.user,
        book=book,
    )
    if not is_created:
        wishlist.delete()

    return Response({'is_wishlisted': is_created})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def collection_toggle(request, book_pk):
    book = Book.objects.filter(pk=book_pk).first()
    if book is None:
        return Response(
            {'error': '도서를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    collection, is_created = Collection.objects.get_or_create(
        user=request.user,
        book=book,
    )
    if not is_created:
        collection.delete()

    return Response({'is_collected': is_created})


@api_view(['POST'])
@permission_classes([AllowAny])
def book_materialize(request):
    isbn = (request.data.get('isbn') or '').strip()
    if not isbn:
        return Response({'error': 'isbn 필수'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        book = materialize_book(request.data)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    serializer = BookDetailSerializer(book, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wishlist_list(request):
    wishlists = Wishlist.objects.filter(
        user=request.user,
    ).select_related('book').prefetch_related('book__genres').order_by(
        '-created_at',
        '-id',
    )
    serializer = WishlistSerializer(wishlists, many=True)
    return Response(serializer.data)
