import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type

def is_valid(phone_number: str) -> bool:

    return carrier._is_mobile(number_type(phonenumbers.parse(phone_number)))