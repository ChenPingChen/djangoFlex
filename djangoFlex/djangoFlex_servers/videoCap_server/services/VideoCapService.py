import logging
from django.db import transaction
from ..models import VideoCapConfig, CurrentFrame
from ..tasks import capture_loop

logger = logging.getLogger(__name__)

class VideoCapService:
    def __init__(self):
        self.configs = {}
        self._load_configs()

    def _load_configs(self):
        for config in VideoCapConfig.objects.filter(is_active=True):
            self.configs[config.rtmp_url] = config
            self.start_server(config.rtmp_url)

    def start_server(self, rtmp_url):
        config, created = VideoCapConfig.objects.get_or_create(rtmp_url=rtmp_url)
        if created:
            config.name = f"Config_{config.id}"
            config.save()

        self.configs[rtmp_url] = config
        config.is_active = True
        config.save()

        capture_loop.delay(rtmp_url)
        return True, "Server started successfully"

    def stop_server(self, rtmp_url):
        if rtmp_url not in self.configs:
            return False, "Server not running"

        config = self.configs[rtmp_url]
        config.is_active = False
        config.save()

        with transaction.atomic():
            CurrentFrame.objects.filter(config=config).delete()

        return True, "Server stopped successfully"

    def check_server_status(self, rtmp_url):
        return self.configs.get(rtmp_url, VideoCapConfig.objects.get(rtmp_url=rtmp_url)).is_active