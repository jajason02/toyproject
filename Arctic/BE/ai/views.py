import json
from time import perf_counter

import httpx
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Follow
from books.models import Book, Collection, Review, Wishlist

from .models import AIWritingLog, CreationComment, CreationCommentLike, CreationLike, WritingDraft
from .serializers import AIWritingLogSerializer, BookRecommendationSerializer, CreationCommentSerializer, WritingDraftSerializer
from .services.recommendation import (
    next_kst_midnight,
)
from .services.precompute import (
    cached_feed,
    cached_recommendations,
    get_or_create_daily_from_cache,
    rebuild_user_recommendation_cache,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def legacy_recommendations(request):
    user = request.user

    excluded_book_ids = set(
        Review.objects.filter(user=user).values_list('book_id', flat=True)
    ) | set(
        Wishlist.objects.filter(user=user).values_list('book_id', flat=True)
    )

    # Tier 1: 팔로우 유저가 4점 이상 준 도서
    followed_user_ids = Follow.objects.filter(
        from_user=user
    ).values_list('to_user_id', flat=True)

    tier1 = list(
        Book.objects.filter(
            reviews__user_id__in=followed_user_ids,
            reviews__rating__gte=4,
        )
        .exclude(id__in=excluded_book_ids)
        .prefetch_related('genres')
        .distinct()
    )

    # Tier 2: 관심 장르 도서 (UserGenre.genre_id FK 기준)
    user_genre_ids = user.preferred_genres.values_list('genre_id', flat=True)

    tier1_ids = {book.id for book in tier1}
    tier2 = list(
        Book.objects.filter(genres__id__in=user_genre_ids)
        .exclude(id__in=excluded_book_ids)
        .exclude(id__in=tier1_ids)
        .prefetch_related('genres')
        .order_by('-average_rating')
        .distinct()
    )

    result = tier1 + tier2

    # Cold Start: 팔로우/장르 데이터 없는 신규 유저
    if not result:
        result = list(
            Book.objects.exclude(id__in=excluded_book_ids)
            .prefetch_related('genres')
            .order_by('-average_rating')[:10]
        )

    serializer = BookRecommendationSerializer(result[:10], many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations(request):
    started_at = perf_counter()
    cached = cached_recommendations(request.user)
    cache_hit = bool(cached)
    if not cached:
        rebuild_user_recommendation_cache(request.user)
        cached = cached_recommendations(request.user)

    recommendation, now = get_or_create_daily_from_cache(
        request.user,
        cached,
    )
    if recommendation is None:
        return Response(
            {'detail': '추천할 수 있는 책이 없습니다.'},
            status=404,
        )

    book_ids = {
        recommendation.book_id,
        *(entry.book_id for entry in cached),
    }
    wishlist_book_ids = set(
        Wishlist.objects.filter(
            user=request.user,
            book_id__in=book_ids,
        ).values_list('book_id', flat=True),
    )
    collection_book_ids = set(
        Collection.objects.filter(
            user=request.user,
            book_id__in=book_ids,
        ).values_list('book_id', flat=True),
    )
    serializer_context = {
        'request': request,
        'wishlist_book_ids': wishlist_book_ids,
        'collection_book_ids': collection_book_ids,
    }
    serializer = BookRecommendationSerializer(
        recommendation.book,
        context=serializer_context,
    )
    feed = cached_feed(
        cached,
        excluded_book_id=recommendation.book_id,
    )
    feed_data = [
        {
            'book': BookRecommendationSerializer(
                entry.book,
                context=serializer_context,
            ).data,
            'scores': entry.scores,
            'candidate_sources': entry.reasons,
        }
        for entry in feed
    ]
    response = Response({
        'date': recommendation.recommendation_date,
        'timezone': 'Asia/Seoul',
        'next_refresh_at': next_kst_midnight(now).isoformat(),
        'daily': {
            'book': serializer.data,
            'scores': recommendation.scores,
            'candidate_sources': recommendation.candidate_sources,
        },
        'feed': feed_data,
    })
    elapsed_ms = (perf_counter() - started_at) * 1000
    response['X-Recommendation-Cache'] = 'HIT' if cache_hit else 'MISS'
    response['Server-Timing'] = (
        f'recommendation;dur={elapsed_ms:.2f}'
    )
    return response


def _proxy_to_ai(endpoint, payload):
    url = f"{settings.AI_SERVER_URL}{endpoint}"
    try:
        response = httpx.post(url, json=payload, timeout=95.0)
        response.raise_for_status()
        return Response(response.json())
    except httpx.TimeoutException:
        return Response({'error': 'AI 서버 응답 시간이 초과되었습니다.'}, status=504)
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get('detail', 'AI 서버 오류가 발생했습니다.')
        except Exception:
            detail = 'AI 서버 오류가 발생했습니다.'
        return Response({'error': detail}, status=e.response.status_code)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_reviews(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    reviews = list(book.reviews.values_list('content', flat=True))

    if len(reviews) < 3:
        return Response({'error': '리뷰가 3개 미만이면 분석할 수 없습니다.'}, status=400)

    response = _proxy_to_ai('/analyze_reviews', {'reviews': reviews})

    if response.status_code == 200:
        AIWritingLog.objects.create(
            user=request.user,
            request_type='analysis',
            input_text=json.dumps(reviews, ensure_ascii=False),
            output_text=json.dumps(response.data, ensure_ascii=False),
        )
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_ideas(request):
    genre = request.data.get('genre', '')
    keywords = request.data.get('keywords', '')

    if not genre or not keywords:
        return Response({'error': 'genre와 keywords는 필수입니다.'}, status=400)

    history = request.data.get('history', [])
    response = _proxy_to_ai('/generate_ideas', {'genre': genre, 'keywords': keywords, 'history': history})

    if response.status_code == 200:
        AIWritingLog.objects.create(
            user=request.user,
            request_type='idea',
            input_text=json.dumps({'genre': genre, 'keywords': keywords}, ensure_ascii=False),
            output_text=json.dumps(response.data, ensure_ascii=False),
        )
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_plot(request):
    idea = request.data.get('idea', '')

    if not idea:
        return Response({'error': 'idea는 필수입니다.'}, status=400)

    history = request.data.get('history', [])
    response = _proxy_to_ai('/suggest_plot', {'idea': idea, 'history': history})

    if response.status_code == 200:
        AIWritingLog.objects.create(
            user=request.user,
            request_type='plot',
            input_text=idea,
            output_text=json.dumps(response.data, ensure_ascii=False),
        )
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def correct_text(request):
    text = request.data.get('text', '')

    if not text:
        return Response({'error': 'text는 필수입니다.'}, status=400)

    history = request.data.get('history', [])
    response = _proxy_to_ai('/correct_text', {'text': text, 'history': history})

    if response.status_code == 200:
        AIWritingLog.objects.create(
            user=request.user,
            request_type='correction',
            input_text=text,
            output_text=json.dumps(response.data, ensure_ascii=False),
        )
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_story_seeds(request):
    genre = request.data.get('genre', '')
    keywords = request.data.get('keywords', '')

    if not genre or not keywords:
        return Response({'error': 'genre와 keywords는 필수입니다.'}, status=400)

    history = request.data.get('history', [])
    return _proxy_to_ai('/ask_story_seeds', {'genre': genre, 'keywords': keywords, 'history': history})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def writing_logs(request):
    logs = AIWritingLog.objects.filter(user=request.user)
    serializer = AIWritingLogSerializer(logs, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def drafts(request):
    if request.method == 'GET':
        qs = WritingDraft.objects.filter(user=request.user)
        return Response(WritingDraftSerializer(qs, many=True, context={'request': request}).data)
    serializer = WritingDraftSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(WritingDraftSerializer(serializer.instance, context={'request': request}).data, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def draft_detail(request, pk):
    draft = get_object_or_404(WritingDraft, pk=pk, user=request.user)
    if request.method == 'DELETE':
        draft.delete()
        return Response(status=204)
    if request.method == 'PATCH':
        serializer = WritingDraftSerializer(draft, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(WritingDraftSerializer(draft, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def draft_like_toggle(request, pk):
    draft = get_object_or_404(WritingDraft, pk=pk, is_public=True)
    like, created = CreationLike.objects.get_or_create(user=request.user, draft=draft)
    if not created:
        like.delete()
        is_liked = False
    else:
        is_liked = True
    return Response({'is_liked': is_liked, 'like_count': draft.likes.count()})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def draft_comments(request, pk):
    draft = get_object_or_404(WritingDraft, pk=pk, is_public=True)
    if request.method == 'POST':
        serializer = CreationCommentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, draft=draft)
        return Response(serializer.data, status=201)
    comments = draft.comments.select_related('user').all()
    return Response(CreationCommentSerializer(comments, many=True, context={'request': request}).data)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def draft_comment_detail(request, comment_pk):
    comment = get_object_or_404(CreationComment, pk=comment_pk, user=request.user)
    if request.method == 'DELETE':
        comment.delete()
        return Response(status=204)
    serializer = CreationCommentSerializer(comment, data=request.data, partial=True, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def draft_comment_like_toggle(request, comment_pk):
    comment = get_object_or_404(CreationComment, pk=comment_pk, draft__is_public=True)
    like, created = CreationCommentLike.objects.get_or_create(
        user=request.user,
        comment=comment,
    )
    if not created:
        like.delete()
        is_liked = False
    else:
        is_liked = True
    return Response({'is_liked': is_liked, 'like_count': comment.likes.count()})
