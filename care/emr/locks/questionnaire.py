from django.conf import settings

from care.utils.lock import Lock


class QuestionnaireLock(Lock):
    def __init__(self, questionnaire, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:questionnaire:{questionnaire.id}"
        self.timeout = timeout
