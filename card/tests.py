from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from unittest.mock import patch
from .models import Card, Factor

class CardTest(TestCase):
    
    def setUp(self):
        myUser = get_user_model()
        self.user = myUser.objects.create(username="test",phone_number="+989998887766",email="test@test.com")
        self.user.set_password("test1234@")
        self.user.save()

    def test_create_card(self):
        
        expected = reverse("auth:userpanel")
        url = reverse("auth:create_card_call",kwargs={"user_id":self.user.id})

        # if succesful => redirect to userpanel
        success_response = self.client.get(url)
        self.assertEqual(success_response.status_code,302)

        card = Card.objects.filter(owner=self.user).exists()
        self.assertTrue(card)
        
        # card already exists => BadRequest
        fail_response = self.client.get(url)
        self.assertEqual(fail_response.status_code, 400)


class CardViewTests(TestCase):

    def setUp(self):
        myUser = get_user_model()
        # sender
        self.user1 = myUser.objects.create(username="user1", phone_number="+989998887761", email="user1@test.com")
        self.user1.set_password("pass1234")
        self.user1.save()

        # receiver
        self.user2 = myUser.objects.create(username="user2", phone_number="+989998887762", email="user2@test.com")
        self.user2.set_password("pass1234")
        self.user2.save()

        # Create card for user 1 (sender)
        self.card1 = Card.objects.create(owner=self.user1, secret_key="123456", balance=1000)
        # Create card for user 2 (receiver)
        self.card2 = Card.objects.create(owner=self.user2, secret_key="123456", balance=500)

        # Clear cache before each test
        cache.clear()

    def test_pay_factor_not_logged_in(self):
        # Access pay-factor view when not logged in => redirect to login
        url = reverse("payfactor", kwargs={"paylink": "some-link"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("auth:login")))

    def test_pay_factor_no_card(self):
        # Create a user with no card
        myUser = get_user_model()
        user_no_card = myUser.objects.create(username="nocard", phone_number="+989998887763", email="nocard@test.com")
        user_no_card.set_password("pass1234")
        user_no_card.save()

        self.client.force_login(user_no_card)
        url = reverse("payfactor", kwargs={"paylink": "some-link"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "no_card")

    def test_pay_factor_not_found(self):
        # User has a card, but the paylink does not exist
        self.client.force_login(self.user1)
        url = reverse("payfactor", kwargs={"paylink": "non-existent-link"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_pay_factor_same_card(self):
        # User tries to pay a factor that has their own card as the recipient (to)
        factor = Factor.objects.create(to=self.card1, amount=100, description="Test factor")
        self.client.force_login(self.user1)
        url = reverse("payfactor", kwargs={"paylink": factor.pay_link})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "same_card")

    def test_pay_factor_already_paid(self):
        # Factor is already paid (status="P")
        factor = Factor.objects.create(to=self.card2, from_u=self.card1, amount=100, status="P", description="Paid factor")
        self.client.force_login(self.user1)
        url = reverse("payfactor", kwargs={"paylink": factor.pay_link})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["payed"])
        self.assertEqual(response.context["factor"], factor)

    def test_pay_factor_insufficient_balance(self):
        # Factor amount is greater than the card balance
        factor = Factor.objects.create(to=self.card2, amount=1000, description="Large factor")
        self.client.force_login(self.user1)
        url = reverse("payfactor", kwargs={"paylink": factor.pay_link})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "balance")

    def test_pay_factor_success(self):
        # Successful payment
        factor = Factor.objects.create(to=self.card2, amount=200, description="Valid factor")
        self.client.force_login(self.user1)
        url = reverse("payfactor", kwargs={"paylink": factor.pay_link})
        
        # Add a dummy cache value to verify invalidation
        cache.set("unpaid_factors", "dummy")

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["payed"])

        # Check balance updates
        self.card1.refresh_from_db()
        self.card2.refresh_from_db()
        
        self.assertEqual(self.card2.balance, 700) # 500 + 200
        self.assertAlmostEqual(self.card1.balance, 797, delta=1)

        # Check factor updates
        factor.refresh_from_db()
        self.assertEqual(factor.status, "P")
        self.assertIsNotNone(factor.payed_date)

        # Check cache invalidation
        self.assertIsNone(cache.get("unpaid_factors"))


class TransferViewTests(TestCase):

    def setUp(self):
        myUser = get_user_model()
        # Create user 1 (sender)
        self.user1 = myUser.objects.create(username="user1", phone_number="+989998887761", email="user1@test.com")
        self.user1.set_password("pass1234")
        self.user1.save()

        # Create user 2 (receiver)
        self.user2 = myUser.objects.create(username="user2", phone_number="+989998887762", email="user2@test.com")
        self.user2.set_password("pass1234")
        self.user2.save()

        # Create card for user 1 (sender)
        self.card1 = Card.objects.create(owner=self.user1, secret_key="123456", balance=1000)
        # Create card for user 2 (receiver)
        self.card2 = Card.objects.create(owner=self.user2, secret_key="123456", balance=500)

    def test_transfer_not_logged_in(self):
        # Access transfer view when not logged in => redirect to login
        url = reverse("transfer")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("auth:login")))

    def test_transfer_get(self):
        # GET request returns transfer.html with form
        self.client.force_login(self.user1)
        url = reverse("transfer")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_transfer_post_invalid(self):
        # POST request with invalid form data
        self.client.force_login(self.user1)
        url = reverse("transfer")
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_transfer_post_no_card(self):
        # User has no active card
        myUser = get_user_model()
        user_no_card = myUser.objects.create(username="nocard", phone_number="+989998887763", email="nocard@test.com")
        user_no_card.set_password("pass1234")
        user_no_card.save()

        self.client.force_login(user_no_card)
        url = reverse("transfer")
        response = self.client.post(url, data={
            "to": self.card2.card_number,
            "amount": 100,
            "description": "Transfer to card 2"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "nocard")

    def test_transfer_post_invalid_dest_card(self):
        # Destination card does not exist
        invalid_card_num = "12345678-1234-1234-1234-123456789012"
        self.client.force_login(self.user1)
        url = reverse("transfer")
        response = self.client.post(url, data={
            "to": invalid_card_num,
            "amount": 100,
            "description": "Transfer to invalid card"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "unvalid card")

    def test_transfer_post_success(self):
        # Valid transfer should create Factor and redirect to payfactor page
        self.client.force_login(self.user1)
        url = reverse("transfer")
        response = self.client.post(url, data={
            "to": self.card2.card_number,
            "amount": 100,
            "description": "Transfer to card 2"
        })
        
        # Should redirect to payfactor
        factor = Factor.objects.filter(to=self.card2, amount=100, description="Transfer to card 2").first()
        self.assertIsNotNone(factor)
        expected_redirect = reverse("payfactor", kwargs={"paylink": factor.pay_link})
        self.assertRedirects(response, expected_redirect)
