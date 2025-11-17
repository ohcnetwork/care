from enum import Enum


class MailTypeChoices(str, Enum):
    create = "create_password"
    reset = "reset_password"
