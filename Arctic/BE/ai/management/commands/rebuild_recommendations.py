from time import perf_counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ai.services.precompute import (
    rebuild_all_recommendations,
    rebuild_user_recommendation_cache,
)


class Command(BaseCommand):
    help = '저장된 모델로 책 통계, 사용자 선호, 추천 캐시를 다시 계산합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='특정 사용자 추천 캐시만 다시 계산합니다.',
        )

    def handle(self, *args, **options):
        started_at = perf_counter()
        user_id = options.get('user_id')
        if user_id is None:
            result = rebuild_all_recommendations(retrain_models=False)
            elapsed_seconds = perf_counter() - started_at
            self.stdout.write(self.style.SUCCESS(
                f"전체 추천 캐시 {result['cache_rows']}건을 "
                f"{elapsed_seconds:.2f}초에 갱신했습니다.",
            ))
            return

        user = get_user_model().objects.filter(id=user_id).first()
        if user is None:
            raise CommandError(f'사용자 {user_id}을(를) 찾을 수 없습니다.')
        count = rebuild_user_recommendation_cache(user)
        elapsed_seconds = perf_counter() - started_at
        self.stdout.write(self.style.SUCCESS(
            f'사용자 {user_id}의 추천 캐시 {count}건을 '
            f'{elapsed_seconds:.2f}초에 갱신했습니다.',
        ))
