from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from .models import Comment, CommentLike, Thread, ThreadLike
from .serializers import (
    CommentSerializer,
    ThreadCreateUpdateSerializer,
    ThreadDetailSerializer,
    ThreadListSerializer,
)


@api_view(['GET', 'POST'])
def thread_list_create(request):
    if request.method == 'GET':
        threads = Thread.objects.select_related('user').prefetch_related(
            'likes',
            'comments',
        ).order_by('-created_at', '-id')

        query = request.query_params.get('q', '').strip()
        search_by = request.query_params.get('search_by', 'all')
        if query:
            if search_by == 'title':
                threads = threads.filter(title__icontains=query)
            elif search_by == 'content':
                threads = threads.filter(content__icontains=query)
            else:
                threads = threads.filter(
                    Q(title__icontains=query) | Q(content__icontains=query),
                )

        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(threads, request)
        serializer = ThreadListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    if not request.user.is_authenticated:
        return Response(
            {'error': '로그인이 필요합니다.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = ThreadCreateUpdateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def thread_detail_update_delete(request, thread_pk):
    thread = Thread.objects.select_related('user').prefetch_related(
        'comments__user',
        'comments__likes',
        'likes',
    ).filter(pk=thread_pk).first()
    if thread is None:
        return Response(
            {'error': '스레드를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'GET':
        serializer = ThreadDetailSerializer(
            thread,
            context={'request': request},
        )
        return Response(serializer.data)

    if not request.user.is_authenticated:
        return Response(
            {'error': '로그인이 필요합니다.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if thread.user != request.user:
        return Response(
            {'error': '본인의 스레드만 수정하거나 삭제할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'DELETE':
        thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ThreadCreateUpdateSerializer(
        thread,
        data=request.data,
        partial=request.method == 'PATCH',
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def thread_like_toggle(request, thread_pk):
    thread = Thread.objects.filter(pk=thread_pk).first()
    if thread is None:
        return Response(
            {'error': '스레드를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    like, is_created = ThreadLike.objects.get_or_create(
        user=request.user,
        thread=thread,
    )
    if not is_created:
        like.delete()

    return Response(
        {
            'is_liked': is_created,
            'like_count': thread.likes.count(),
        },
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_create(request, thread_pk):
    thread = Thread.objects.filter(pk=thread_pk).first()
    if thread is None:
        return Response(
            {'error': '스레드를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CommentSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(user=request.user, thread=thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_like_toggle(request, thread_pk, comment_pk):
    comment = Comment.objects.filter(
        pk=comment_pk,
        thread_id=thread_pk,
    ).first()
    if comment is None:
        return Response(
            {'error': '댓글을 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    like, is_created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment,
    )
    if not is_created:
        like.delete()

    return Response(
        {
            'is_liked': is_created,
            'like_count': comment.likes.count(),
        },
    )


@api_view(['PATCH', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def comment_update_delete(request, thread_pk, comment_pk):
    comment = Comment.objects.filter(
        pk=comment_pk,
        thread_id=thread_pk,
    ).first()
    if comment is None:
        return Response(
            {'error': '댓글을 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if comment.user != request.user:
        return Response(
            {'error': '본인의 댓글만 수정하거나 삭제할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'DELETE':
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CommentSerializer(
        comment,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request},
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
