from time import perf_counter

from django.core.management.base import BaseCommand

from ai.services.precompute import rebuild_all_recommendations


class Command(BaseCommand):
    help = (
        'RandomForest 모델을 다시 학습하고 책 통계, 사용자 선호, '
        '사용자별 추천 캐시를 전체 재생성합니다.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--cache-only',
            action='store_true',
            help='저장된 모델은 유지하고 통계와 추천 캐시만 다시 만듭니다.',
        )

    def handle(self, *args, **options):
        self.stdout.write('추천 데이터 구축을 시작합니다.')
        started_at = perf_counter()
        result = rebuild_all_recommendations(
            retrain_models=not options['cache_only'],
        )
        elapsed_seconds = perf_counter() - started_at
        self.stdout.write(self.style.SUCCESS(
            '추천 데이터 구축 완료\n'
            f"- 사용자: {result['users']}명\n"
            f"- 도서: {result['books']}권\n"
            f"- 추천 캐시: {result['cache_rows']}건\n"
            f"- 모델 파일: {result['model_path']}\n"
            f"- 소요 시간: {elapsed_seconds:.2f}초",
        ))
