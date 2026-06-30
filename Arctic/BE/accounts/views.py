from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Follow
from .serializers import (
    SignUpSerializer,
    UserListSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)


def _first_error_value(value):
    if isinstance(value, dict):
        for nested_value in value.values():
            return _first_error_value(nested_value)
    if isinstance(value, (list, tuple)):
        if value:
            return _first_error_value(value[0])
    if value:
        return str(value)
    return None


def _first_error(serializer):
    message = _first_error_value(serializer.errors)
    if message:
        return message
    return '요청 값이 올바르지 않습니다.'


def _update_profile(request, user):
    data = request.data.copy()
    if hasattr(request.data, 'getlist'):
        genre_ids = request.data.getlist('preferred_genres')
        if genre_ids:
            data.setlist('preferred_genres', genre_ids)

    serializer = UserProfileUpdateSerializer(
        user,
        data=data,
        context={'request': request},
        partial=True,
    )
    if not serializer.is_valid():
        return None, Response(
            {'error': _first_error(serializer)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return serializer.save(), None


@api_view(['POST'])
def signup(request):
    serializer = SignUpSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': _first_error(serializer)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = serializer.save()
    from ai.services.precompute import mark_users_dirty
    mark_users_dirty([user.id], 'user_created')

    return Response(
        {
            'id': user.pk,
            'username': user.username,
            'email': user.email,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def email_availability(request):
    email = request.query_params.get('email', '').strip().lower()
    if not email:
        return Response(
            {'error': '이메일을 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_email(email)
    except DjangoValidationError:
        return Response(
            {'error': '올바른 이메일 형식으로 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    User = get_user_model()
    is_available = not User.objects.filter(email__iexact=email).exists()
    return Response({
        'available': is_available,
        'message': (
            '사용 가능한 이메일입니다.'
            if is_available
            else '이미 사용 중인 이메일입니다.'
        ),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request, user_id=None):
    User = get_user_model()
    profile_user = request.user
    if user_id is not None:
        profile_user = get_object_or_404(User, pk=user_id)

    serializer = UserProfileSerializer(
        profile_user,
        context={'request': request},
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@transaction.atomic
def profile_update(request):
    user, error_response = _update_profile(request, request.user)
    if error_response is not None:
        return error_response

    from ai.services.precompute import mark_users_dirty
    mark_users_dirty([user.id], 'profile_updated')

    serializer = UserProfileSerializer(user, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_toggle(request, user_id):
    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)

    if target_user == request.user:
        return Response(
            {'error': '자기 자신은 팔로우할 수 없습니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    follow = Follow.objects.filter(
        from_user=request.user,
        to_user=target_user,
    ).first()

    if follow is not None:
        follow.delete()
        is_following = False
    else:
        Follow.objects.create(
            from_user=request.user,
            to_user=target_user,
        )
        is_following = True

    return Response(
        {
            'is_following': is_following,
            'follower_count': target_user.followers.count(),
            'following_count': request.user.followings.count(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def follower_list(request, user_id=None):
    User = get_user_model()

    if user_id is not None:
        profile_user = get_object_or_404(User, pk=user_id)
    else:
        profile_user = request.user

    followers = User.objects.filter(
        followings__to_user=profile_user,
    ).order_by('username')
    serializer = UserListSerializer(
        followers,
        many=True,
        context={'request': request},
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def following_list(request, user_id=None):
    User = get_user_model()

    if user_id is not None:
        profile_user = get_object_or_404(User, pk=user_id)
    else:
        profile_user = request.user

    followings = User.objects.filter(
        followers__from_user=profile_user,
    ).order_by('username')
    serializer = UserListSerializer(
        followings,
        many=True,
        context={'request': request},
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_search(request):
    q = request.query_params.get('q', '').strip()
    if len(q) < 2:
        return Response([])
    User = get_user_model()
    users = User.objects.filter(
        Q(username__icontains=q) | Q(email__icontains=q)
    ).exclude(pk=request.user.pk)[:20]
    serializer = UserListSerializer(users, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def cookie_login(request):
    serializer = TokenObtainPairSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    access = str(serializer.validated_data['access'])
    refresh = str(serializer.validated_data['refresh'])
    response = Response({'message': '로그인 성공'})
    response.set_cookie('access', access, httponly=True, samesite='Lax', secure=False, max_age=3600)
    response.set_cookie('refresh', refresh, httponly=True, samesite='Lax', secure=False, max_age=7 * 24 * 3600)
    response.set_cookie('auth_state', '1', httponly=False, samesite='Lax', secure=False, max_age=7 * 24 * 3600)
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def cookie_refresh(request):
    refresh_token = request.COOKIES.get('refresh')
    if not refresh_token:
        return Response({'error': '리프레시 토큰이 없습니다.'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        token = RefreshToken(refresh_token)
        access = str(token.access_token)
    except TokenError:
        response = Response({'error': '리프레시 토큰이 만료되었습니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        response.delete_cookie('access')
        response.delete_cookie('refresh')
        response.delete_cookie('auth_state')
        return response
    response = Response({'message': '토큰 갱신 성공'})
    response.set_cookie('access', access, httponly=True, samesite='Lax', secure=False, max_age=3600)
    return response


@api_view(['POST'])
def logout(request):
    refresh_token = request.COOKIES.get('refresh')
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass
    response = Response(status=status.HTTP_204_NO_CONTENT)
    response.delete_cookie('access')
    response.delete_cookie('refresh')
    response.delete_cookie('auth_state')
    return response
