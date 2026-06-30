from django.db.utils import OperationalError, ProgrammingError
from rest_framework import serializers

from .models import Comment, CommentLike, Thread, ThreadLike


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    profile_image = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'id',
            'user_id',
            'username',
            'profile_image',
            'content',
            'created_at',
            'is_mine',
        )
        read_only_fields = ('id', 'user_id', 'username', 'profile_image', 'created_at')

    def get_profile_image(self, comment):
        image = getattr(comment.user, 'profile_image', None)
        if not image:
            return ''
        image_url = image.url
        request = self.context.get('request')
        if request is None:
            return image_url
        return request.build_absolute_uri(image_url)

    def get_is_mine(self, comment):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return comment.user_id == request.user.id

    def get_like_count(self, comment):
        try:
            return comment.likes.count()
        except (OperationalError, ProgrammingError):
            return 0

    def get_is_liked(self, comment):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        try:
            return CommentLike.objects.filter(
                user=request.user,
                comment=comment,
            ).exists()
        except (OperationalError, ProgrammingError):
            return False


class ThreadListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    profile_image = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    comment_count = serializers.IntegerField(
        source='comments.count',
        read_only=True,
    )

    class Meta:
        model = Thread
        fields = (
            'id',
            'user_id',
            'username',
            'profile_image',
            'title',
            'content',
            'created_at',
            'like_count',
            'comment_count',
        )

    def get_profile_image(self, thread):
        image = getattr(thread.user, 'profile_image', None)
        if not image:
            return ''
        image_url = image.url
        request = self.context.get('request')
        if request is None:
            return image_url
        return request.build_absolute_uri(image_url)


class ThreadDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    profile_image = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = (
            'id',
            'user_id',
            'username',
            'profile_image',
            'title',
            'content',
            'created_at',
            'comments',
            'like_count',
            'is_liked',
            'is_mine',
        )

    def get_profile_image(self, thread):
        image = getattr(thread.user, 'profile_image', None)
        if not image:
            return ''
        image_url = image.url
        request = self.context.get('request')
        if request is None:
            return image_url
        return request.build_absolute_uri(image_url)

    def get_is_liked(self, thread):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return ThreadLike.objects.filter(
            user=request.user,
            thread=thread,
        ).exists()

    def get_is_mine(self, thread):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return thread.user_id == request.user.id


class ThreadCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = ('id', 'title', 'content', 'created_at')
        read_only_fields = ('id', 'created_at')
