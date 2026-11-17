from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_customer_has_unusable_password(self):
        user = get_user_model().objects.create_user(phone="09123456789")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_superuser_requires_password(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_superuser(phone="09123456789")

    def test_superuser_flags(self):
        user = get_user_model().objects.create_superuser(
            phone="09123456789", password="a-strong-test-password"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.has_usable_password())
