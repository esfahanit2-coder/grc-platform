from django.test import TestCase
class ReportingSmokeTests(TestCase):
    def test_import(self): from .views import ManagementDashboardView;self.assertTrue(ManagementDashboardView)
