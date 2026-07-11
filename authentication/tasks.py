from django.core.mail import send_mail
from django.conf import settings

def send_email(email: str, username: str) -> None:
    send_mail(
        subject="Congrats new member",
        message=f"Hi dear {username} \n we wish you best experience \n\n درود {username} به وبسایت من خوش امدید و بهترین تجربه رو برای شما ارزومند هستم",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=True
    )