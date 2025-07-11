from django.utils.timezone import now, timedelta
from .models import Subscription, SubscriptionPlan 

def activate_paid_plan(user):

    subscription = Subscription.objects.filter(user=user, is_active=True).first()
    
    if subscription and subscription.is_expired():
        try:     
            default_plan = SubscriptionPlan.objects.get(duration=6) 
        except SubscriptionPlan.DoesNotExist:
            return 

    subscription, created = Subscription.objects.get_or_create(user=user)

    subscription.subscription_plan = default_plan
    subscription.is_trial = False
    subscription.start_date = now()
    subscription.next_billing_date = now() + timedelta(days=(default_plan.duration * 30))  # Convert months to days
    subscription.save()








import requests
from clients.models import GlobalSMSConfig, TenantSMSConfig


def send_sms(tenant=None, phone_number=None, message=""):  
    config = None
  
    if tenant:
        config = TenantSMSConfig.objects.filter(tenant=tenant).first()

    if not config:
        config = GlobalSMSConfig.objects.first()

    if not config:
        raise Exception("No SMS configuration found.")

    params = {
        "api_key": config.api_key,
        "type": "text",
        "number": phone_number,
        "senderid": config.sender_id or "DefaultSID",
        "message": message,
    }

    try:
        response = requests.get(config.api_url, params=params)
        print("SMS Provider Response:", response.text)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise Exception(f"SMS sending failed: {str(e)}")






# example of sending sms
def notify_payment(student, guardian, paid_amount):
    tenant = student.user.tenant
    phone_number = guardian.phone_number
    message = f"Dear {guardian.name}, your payment of BDT {paid_amount} has been received. Thank you."

    try:
        send_sms(tenant, phone_number, message)
    except Exception as e:
        print("SMS failed:", e)

