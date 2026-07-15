from django.test import TestCase
from .views import pass_validate

class AuthTestCase(TestCase):
    def setUp(self):
        pass
    def test_pass_validate(self):
        # str return means something failed
        self.assertIsInstance(pass_validate("test1234","test1234"),str)
        self.assertIsInstance(pass_validate("test1234","test1234"),str)
        self.assertIsInstance(pass_validate("test1234","test1235"),str)

        self.assertIsInstance(pass_validate("Test1234","Test1234"),str)
        
        self.assertIsInstance(pass_validate("test1234@","test1234@"),str)
        self.assertIsInstance(pass_validate("Test1234@","Test1234!"),str)

        self.assertIsInstance(pass_validate("Test1234@ª","Test1234@ª"),str)

        self.assertIsInstance(pass_validate("Test14@","Test14@"),str)

        # only bool return of pass_validate is True
        self.assertIsInstance(pass_validate("Test1234@","Test1234@"),bool)
    