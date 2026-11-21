"""Point d'entrée unique pour prévenir un utilisateur (dans l'app et par email)."""
import logging

from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def notify(user, kind: str, title: str, content: str, email: bool = True) -> Notification:
    notification = Notification.objects.create(
        user=user, kind=kind, title=title, content=content, channel=Notification.Channel.IN_APP
    )
    if email:
        try:
            send_mail(title, content, None, [user.email])
        except Exception:  # un email en échec ne doit pas annuler l'action métier
            logger.exception("Échec d'envoi d'email à %s (%s)", user.email, kind)
    return notification
