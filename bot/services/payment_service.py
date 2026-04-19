import logging
import uuid
from typing import Optional
from bot.config import settings

logger = logging.getLogger(__name__)


def create_yookassa_payment(amount: float, description: str, return_url: str) -> Optional[dict]:
    try:
        from yookassa import Configuration, Payment
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        payment = Payment.create({
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
        }, str(uuid.uuid4()))
        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "status": payment.status,
        }
    except Exception as e:
        logger.error(f"YooKassa payment creation error: {e}")
        return None


def check_yookassa_payment(payment_id: str) -> Optional[str]:
    """Returns payment status: pending, succeeded, canceled"""
    try:
        from yookassa import Configuration, Payment
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        payment = Payment.find_one(payment_id)
        return payment.status
    except Exception as e:
        logger.error(f"YooKassa check payment error: {e}")
        return None
