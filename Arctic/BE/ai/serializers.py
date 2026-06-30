from rest_framework import serializers

from books.serializers import BookListSerializer

from .models import AIWritingLog, CreationComment, CreationLike, WritingDraft


class BookRecommendationSerializer(BookListSerializer):
    pass


class WritingDraftSerializer(serializers.ModelSerializer):
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = WritingDraft
        fields = (
            'id',
            'title',
            'draft_type',
            'genre',
            'keywords',
            'content',
            'is_public',
            'created_at',
            'like_count',
            'comment_count',
            'is_liked',
        )
        read_only_fields = ('id', 'created_at')

    def get_like_count(self, draft):
        return draft.likes.count()

    def get_comment_count(self, draft):
        return draft.comments.count()

    def get_is_liked(self, draft):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return CreationLike.objects.filter(user=request.user, draft=draft).exists()


class CreationCommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = CreationComment
        fields = ('id', 'user_id', 'username', 'content', 'created_at', 'like_count', 'is_liked')
        read_only_fields = ('id', 'user_id', 'username', 'created_at')

    def get_like_count(self, comment):
        return comment.likes.count()

    def get_is_liked(self, comment):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return comment.likes.filter(user=request.user).exists()


class AIWritingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIWritingLog
        fields = ('id', 'request_type', 'input_text', 'output_text', 'created_at')
        read_only_fields = ('id', 'created_at')
