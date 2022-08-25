import re

from django.core.validators import ValidationError

USERNAME_SYMBOLS = re.compile(r'[\w.@+-@./+-]+')
INVALID_USERNAME_SYMBOLS = 'Недопустимые символы: {value}'


class UsernameValidation:
    def validate_username(self, value):
        if not re.match(USERNAME_SYMBOLS, value):
            raise ValidationError(
                INVALID_USERNAME_SYMBOLS.format(
                    value=[
                        symbol for symbol in value if symbol not in ''.join(
                            re.findall(USERNAME_SYMBOLS, value)
                        )
                    ]
                )
            )
        return value
