
from django.shortcuts import render, get_object_or_404,redirect,reverse
from django.contrib import messages

from clients.models import SubscriptionPlan


def common_view(request):
    plans = SubscriptionPlan.objects.all().order_by('duration')
    for plan in plans:
        plan.features_list = plan.features.split(',') 

    tenant_links = [
        {'name': 'only_core_dashboard', 'url': reverse('core:only_core_dashboard')},
        {'name': 'home', 'url': reverse('core:home')},
        {'name': 'tasks_dashboard', 'url': reverse('tasks:tasks_dashboard')},
    ]
    return render(request, 'commonapp/home.html', {'tenant_links': tenant_links,'plans': plans})




from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.dateparse import parse_datetime



class ReceiveAttendanceDataAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            fingerprint_id = data.get("user_id")
            timestamp = parse_datetime(data.get("timestamp"))
            print(f'[DEBUG] Headers={request.headers}')
            print(f'[DEBUG] Authenticated user={request.user}')

            print(f'[DEBUG] Received fingerprint_id={fingerprint_id}, timestamp={timestamp}')

            if not fingerprint_id or not timestamp:
                return Response({"status": "error", "message": "user_id and timestamp required"}, status=status.HTTP_400_BAD_REQUEST)

            # You can add model saving logic here later

            return Response({"status": "success", "message": "Attendance saved"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





