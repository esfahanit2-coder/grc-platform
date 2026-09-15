from django.test import TestCase
class DocumentsSmokeTests(TestCase):
    def test_models_import(self):
        from .models import Document,DocumentVersion
        self.assertTrue(Document and DocumentVersion)
