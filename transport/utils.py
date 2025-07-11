
from django.utils.timezone import now
from decimal import ROUND_DOWN
from decimal import Decimal
from django.conf import settings


def calculate_penalty_amount(booking):
    penalty_rate_per_hour = Decimal(50.0)
    MAX_PENALTY_CAP = Decimal(getattr(settings, 'MAX_PENALTY_CAP', '500.00')) 
    overdue_seconds = (now() - booking.return_datetime).total_seconds() 
    overdue_hours = overdue_seconds / 3600  
    if overdue_hours <= 0:
        return 0.0
    decimal_overdue = Decimal(overdue_hours)
    overdue_hours = decimal_overdue.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    penalty_amount = penalty_rate_per_hour * overdue_hours
    penalty_decimal = Decimal(penalty_amount)
    penalty_amount = penalty_decimal.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
    if penalty_amount > MAX_PENALTY_CAP:
        penalty_amount = MAX_PENALTY_CAP
    print(overdue_hours,penalty_amount)
    return round(penalty_amount, 2)  
