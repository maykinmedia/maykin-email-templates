import logging
import os
import subprocess
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Context, Template, loader
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .mail_template import validate_template
from .node import locate_package_json
from .settings import get_config
from .utils import variable_help_text

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class MailTemplate(models.Model):
    template_type = models.CharField(_('type'), max_length=50, unique=True)

    remarks = models.TextField(_('remarks'), blank=True, default='', help_text=_('Extra information about the template'))
    subject = models.CharField(_('subject'), max_length=255)
    body = models.TextField(_('body'), help_text=_('Add the body with {{variable}} placeholders'))

    CONFIG = {}
    CHOICES = None

    class Meta:
        verbose_name = _('mail template')
        verbose_name_plural = _('mail templates')

    def __init__(self, *args, **kwargs):
        super(MailTemplate, self).__init__(*args, **kwargs)
        self.CONFIG = get_config()
        self._package_json_dir = os.path.dirname(locate_package_json())

        env = os.environ.copy()
        if settings.ADD_BIN_PATH:
            env['PATH'] = '{}:{}/bin/'.format(env['PATH'], settings.BIN_PATH)

        self.env = env

    def __str__(self):
        return self.template_type

    def clean(self):
        validate_template(self)

    def render(self, context, subj_context=None):
        if not subj_context:
            subj_context = context

        tpl_subject = Template(self.subject)
        tpl_body = Template(self.body)

        ctx = Context(context)
        subj_ctx = Context(subj_context)

        partial_body = tpl_body.render(ctx)
        template = loader.get_template('mail/_base.html')
        current_site = get_current_site(None)
        body = template.render({'domain': current_site.domain, 'content': partial_body}, None)

        with NamedTemporaryFile() as temp_file:
            temp_file.write(bytes(body, 'UTF-8'))
            extra_env = self.env
            process = subprocess.Popen(
                "inject-inline-styles.js {}".format(temp_file.name), shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=extra_env, universal_newlines=True, cwd=self._package_json_dir
            )

            out, err = process.communicate()
            if err:
                raise Exception(err)

            return tpl_subject.render(subj_ctx), mark_safe(out)

    def send_email(self, to_addresses, context, subj_context=None, txt=False, attachments=None):
        """
        You can pass the context only. We will pass the context to the subject context when we don't
        have a subject context.

        @param attachments: List of tuples, where the tuple can be one of two forms:
                            `(<absolute file path>, [mime type])` or
                            `(<filename>, <content>, [mime type])`
        """
        subject, body = self.render(context, subj_context)
        text_body = txt or strip_tags(body)

        email_message = EmailMultiAlternatives(subject=subject, body=text_body, from_email=settings.DEFAULT_FROM_EMAIL, to=to_addresses)
        email_message.attach_alternative(body, 'text/html')

        if attachments:
            for attachment in attachments:
                if not attachment or not isinstance(attachment, tuple):
                    raise ValueError('Attachments should be passed as a list of tuples.')
                if os.path.isabs(attachment[0]):
                    email_message.attach_file(*attachment)
                else:
                    email_message.attach(*attachment)

        return email_message.send()

    def get_variable_help_text(self):
        return variable_help_text(self.template_type)
