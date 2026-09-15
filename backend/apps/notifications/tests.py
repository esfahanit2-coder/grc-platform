from django.test import TestCase
class NotificationSmokeTests(TestCase):
    def test_imports(self):
        from .models import Notification
        self.assertTrue(Notification)
