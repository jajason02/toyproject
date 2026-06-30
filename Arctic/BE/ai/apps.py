import os
import sys
import threading
from time import perf_counter

from django.apps import AppConfig
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError


class AiConfig(AppConfig):
    name = 'ai'

    def ready(self):
        import ai.signals  # noqa: F401

        if not getattr(settings, 'RECOMMENDATION_AUTO_BOOTSTRAP', True):
            return
        if 'runserver' not in sys.argv:
            return
        is_reloader_child = os.environ.get('RUN_MAIN') == 'true'
        is_no_reload = '--noreload' in sys.argv
        if not is_reloader_child and not is_no_reload:
            return

        # 최초 1회 구축은 무거우므로 서버 기동을 막지 않도록 백그라운드에서 실행한다.
        # ensure_recommendation_bootstrap()는 이미 구축이 끝났으면 즉시 반환한다.
        threading.Thread(target=self._bootstrap_recommendations, daemon=True).start()

    def _bootstrap_recommendations(self):
        from django.db import close_old_connections

        from .services.precompute import ensure_recommendation_bootstrap

        close_old_connections()
        started_at = perf_counter()
        try:
            result = ensure_recommendation_bootstrap()
        except (OperationalError, ProgrammingError):
            print(
                '[recommendation] 추천 테이블이 준비되지 않았습니다. '
                'python manage.py migrate를 먼저 실행해 주세요.',
            )
            return
        except Exception as error:
            print(f'[recommendation] 최초 추천 데이터 구축 실패: {error}')
            return
        finally:
            close_old_connections()
        if result:
            elapsed_seconds = perf_counter() - started_at
            print(
                '[recommendation] 최초 추천 데이터 구축 완료: '
                f"사용자 {result['users']}명, "
                f"캐시 {result['cache_rows']}건, "
                f"{elapsed_seconds:.2f}초",
            )
