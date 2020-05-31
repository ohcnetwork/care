from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.accounts import constants as accounts_constants


class BaseMailer:
    """
     All Mailers should extend this Mailer
     """

    context = None
    template_name = None
    to_email_list = None
    from_email = settings.DEFAULT_FROM_EMAIL
    bcc = None
    cc = None
    file_path = None

    email_template_name_prefix = "emails/"

    def __init__(
        self,
        context=None,
        template_name=None,
        to_email_list=None,
        from_email=None,
        bcc=None,
        cc=None,
        file_path=None,
        **kwargs,
    ):
        self.context = context or self.context or {}
        self.template_name = template_name or self.get_template_name()
        self.to_email_list = to_email_list or self.to_email_list
        self.from_email = from_email or self.from_email
        self.bcc = bcc or self.bcc
        self.cc = cc or self.cc
        self.kwargs = kwargs
        self.file_path = file_path or self.file_path

    def get_template_name(self):
        """
        Prefix email_template_name_prefix before template_name
        """
        return "".join([self.email_template_name_prefix, self.template_name])

    @staticmethod
    def send_mail(
        context,
        template_name,
        to_email_list,
        from_email=settings.DEFAULT_FROM_EMAIL,
        bcc=None,
        cc=None,
        file_path=None,
    ):
        """
        A static method that takes inputs and sends mail & sms
        """
        if bcc is None:
            bcc = []

        subject = render_to_string("{}{}.txt".format(template_name, "sub"), context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=render_to_string("{}{}.txt".format(template_name, "msg"), context),
            from_email=from_email,
            to=to_email_list,
            bcc=bcc,
            cc=cc,
            alternatives=[(render_to_string("{}{}.html".format(template_name, "msg"), context), "text/html",),],
        )
        # attach file
        if file_path:
            message.attach_file(file_path)
        message.send()

    def send(self):
        self.send_mail(
            context=self.get_context(),
            template_name=self.template_name,
            to_email_list=self.to_email_list,
            from_email=self.from_email,
            bcc=self.bcc,
            cc=self.cc,
            file_path=self.file_path,
        )

    def get_context(self):
        return self.context


class ForgotPasswordMailer(BaseMailer):
    """
    Mailer used to Send Password Reset Emails to a User.
    """

    template_name = "accounts/reset_password/"

    def send(self):
        """
        Set parameters to send the Mail
        """
        user = self.kwargs.get("user")
        self.context.update(
            {
                "user": user,
                "reset_password_url": f"{settings.WEBAPP_BASE_URL}/{accounts_constants.RESET_PASSWORD_BASE_URL}/"
                f"{self.kwargs.get('uid')}/{self.kwargs.get('token')}",
            }
        )
        self.to_email_list = [user.email]
        super().send()
