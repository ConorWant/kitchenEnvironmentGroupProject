from django.apps import AppConfig
import threading
import time

class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "monitor"

    def ready(self):
        # Avoid running twice due to Django's auto-reloader
        import os
        if os.environ.get("RUN_MAIN") != "true":
            return

        thread = threading.Thread(target=self._fetch_loop, daemon=True)
        thread.start()

    def _fetch_loop(self):
        from django.core.management import call_command
        time.sleep(5)  # wait for server to fully start
        while True:
            try:
                call_command("fetch_pilsworth")
            except Exception as e:
                print(f"[AUTO FETCH ERROR] {e}")
            time.sleep(10)