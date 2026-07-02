import csv
import io

from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from django.core.cache import cache
from datetime import timedelta
from django.utils.dateparse import parse_datetime, parse_date
from django.db.models import OuterRef, Subquery, Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import views, status, viewsets

from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication

from core.permissions import Authenticated, Visitors

from datetime import datetime, timezone

from api.models import Group, Circuit, ServerLog
from api.serializers import (
    SignInSerializer,
    SignUpSerializer,
    SignResponseSerializer,
    UserSerializer,
    GroupSerializer,
    CircuitSerializer,
    CircuitViewSetSerializer,
    ServerLogSerializer,
    ServerLogChartSerializer
)

#       #       #       #       #       #       #       #       #       #       #       #

# Index 200
def index(request):
    return HttpResponse('.')

#       #       #       #       #       #       #       #       #       #       #       #

# User ViewSet
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

# Group ViewSet
class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()

# Circuit ViewSet
class CircuitViewSet(viewsets.ModelViewSet):
    serializer_class = CircuitViewSetSerializer
    queryset = Circuit.objects.all()

#       #       #       #       #       #       #       #       #       #       #       #

# Create new log
class LogIngestView(APIView):

    def post(self, request, *args, **kwargs):

        raw_data = request.body.decode("utf-8").strip()

        if not raw_data:
            return Response({"error": "Empty payload"}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.reader(io.StringIO(raw_data))
        logs_to_create = []
        circuits_cache = {}

        for row in reader:
            try:
                # Saltar líneas vacías o con error
                if not row or len(row) < 11:
                    continue

                # Parse de valores
                timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M")
                timestamp = timestamp.replace(tzinfo=timezone.utc)
                source = row[1]
                target_host = row[2]
                min_value = float(row[7])
                avg_value = float(row[8])
                max_value = float(row[9])
                stddev_value = float(row[10])

                # Buscar o crear Circuit (con cache local para eficiencia)
                circuit = circuits_cache.get(target_host)
                if not circuit:
                    circuit, _ = Circuit.objects.get_or_create(target_host=target_host)
                    circuits_cache[target_host] = circuit

                # Crear objeto ServerLog
                logs_to_create.append(ServerLog(
                    timestamp=timestamp,
                    source_host=source,
                    circuit=circuit,
                    min_value=min_value,
                    avg_value=avg_value,
                    max_value=max_value,
                    stddev_value=stddev_value
                ))

            except Exception as e:
                print(f"⚠️ Error procesando línea: {row} -> {e}")
                continue

        # Inserción masiva con ignore_conflicts para evitar duplicados
        if logs_to_create:
            ServerLog.objects.bulk_create(logs_to_create, ignore_conflicts=True)
            print(f"✅ Rows insert success")

        return Response(
            {"status": "ok", "inserted": len(logs_to_create)},
            status=status.HTTP_200_OK
        )

#       #       #       #       #       #       #       #       #       #       #       #

# Create source query
class ServerLogQueryView(APIView):
    permission_classes = [Authenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):

        # Query params
        specific_date = request.query_params.get("timestamp")
        date_start = request.query_params.get("date_start") or request.query_params.get("start")
        date_end = request.query_params.get("date_end") or request.query_params.get("end")
        time_start = request.query_params.get("time_start")
        time_end = request.query_params.get("time_end")
        source = request.query_params.get("source_host")
        target = request.query_params.get("target_host")

        # Get all logs
        groups = Group.objects.all()
        circuit = Circuit.objects.get(target_host=target)
        logs = ServerLog.objects.select_related("circuit").all()

        # Filter for specific day
        if specific_date:
            try:
                date_obj = parse_date(specific_date)
                if date_obj:
                    start_of_day = datetime.combine(date_obj, datetime.min.time())
                    end_of_day = datetime.combine(date_obj, datetime.max.time())
                    logs = logs.filter(timestamp__range=[start_of_day, end_of_day])
            except Exception:
                pass

        # Filter by date ranges
        if date_start:
            try:
                parsed_date = parse_date(date_start)
                if parsed_date:
                    logs = logs.filter(timestamp__date__gte=parsed_date)
            except Exception:
                pass

        if date_end:
            try:
                parsed_date = parse_date(date_end)
                if parsed_date:
                    logs = logs.filter(timestamp__date__lte=parsed_date)
            except Exception:
                pass

        # Filter by daily time window
        parsed_time_start = None
        if time_start:
            try:
                parts = [int(p) for p in time_start.split(":")]
                if len(parts) == 2:
                    parsed_time_start = datetime.min.time().replace(hour=parts[0], minute=parts[1])
                elif len(parts) >= 3:
                    parsed_time_start = datetime.min.time().replace(hour=parts[0], minute=parts[1], second=parts[2])
            except Exception:
                pass

        parsed_time_end = None
        if time_end:
            try:
                parts = [int(p) for p in time_end.split(":")]
                if len(parts) == 2:
                    parsed_time_end = datetime.min.time().replace(hour=parts[0], minute=parts[1], second=59)
                elif len(parts) >= 3:
                    parsed_time_end = datetime.min.time().replace(hour=parts[0], minute=parts[1], second=parts[2])
            except Exception:
                pass

        if parsed_time_start and parsed_time_end:
            if parsed_time_start <= parsed_time_end:
                logs = logs.filter(timestamp__time__range=(parsed_time_start, parsed_time_end))
            else:
                logs = logs.filter(Q(timestamp__time__gte=parsed_time_start) | Q(timestamp__time__lte=parsed_time_end))
        elif parsed_time_start:
            logs = logs.filter(timestamp__time__gte=parsed_time_start)
        elif parsed_time_end:
            logs = logs.filter(timestamp__time__lte=parsed_time_end)

        # Create source filter
        if source:
            logs = logs.filter(source_host__icontains=source)

        # Create target filter (now via related Circuit)
        if target:
            logs = logs.filter(circuit__target_host__icontains=target)

        # Create security limit
        logs = logs.order_by("timestamp")[:300]

        # Create response
        groups = GroupSerializer(groups, many=True)

        # Get absolute latest log of this circuit to calculate its current status
        latest_log = ServerLog.objects.filter(circuit=circuit).order_by("-timestamp").first()

        # Calculate status of the circuit based on the last log timestamp in the database (Option B)
        last_log = ServerLog.objects.order_by("-timestamp").first()
        is_db_aware = False
        if last_log and last_log.timestamp:
            is_db_aware = dj_timezone.is_aware(last_log.timestamp)

        if last_log and last_log.timestamp:
            limit_time = last_log.timestamp - timedelta(hours=1)
        else:
            limit_time = (dj_timezone.now() if is_db_aware else datetime.utcnow()) - timedelta(hours=1)

        if latest_log:
            if latest_log.timestamp and latest_log.timestamp < limit_time:
                circuit_status_name = "down"
            elif latest_log.min_value <= circuit.range_down:
                circuit_status_name = "worker"
            else:
                circuit_status_name = "protected"
        else:
            circuit_status_name = "unknown"

        circuit_data = CircuitSerializer(circuit).data
        circuit_data["status_name"] = circuit_status_name

        # Serialize and add status_name to logs
        logs_data = []
        for log in logs:
            log_serialized = ServerLogChartSerializer(log).data

            # Classify as worker or protected
            if log.min_value <= circuit.range_down:
                status_name = "worker"
            else:
                status_name = "protected"

            log_serialized["status_name"] = status_name
            logs_data.append(log_serialized)

        response = {
            "groups" : groups.data,
            "circuit" : circuit_data,
            "logs" : logs_data
        }

        print( response )

        return Response(response, status=status.HTTP_200_OK)

#       #       #       #       #       #       #       #       #       #       #       #

# Last source created
class LastLogPerSourceView(APIView):

    def get(self, request):

        latest_log_subquery = (
            ServerLog.objects
            .filter(
                source_host=OuterRef("source_host"),
                circuit=OuterRef("circuit")
            )
            .order_by("-timestamp")
        )

        queryset = (
            ServerLog.objects
            .filter(pk=Subquery(latest_log_subquery.values("pk")[:1]))
            .select_related("circuit")
            .order_by("source_host", "circuit__target_host")
        )

        # Get the latest log to base our time limit on (Option B)
        last_log = ServerLog.objects.order_by("-timestamp").first()
        is_db_aware = False
        if last_log and last_log.timestamp:
            is_db_aware = dj_timezone.is_aware(last_log.timestamp)

        if last_log and last_log.timestamp:
            limit_time = last_log.timestamp - timedelta(hours=1)
        else:
            limit_time = (dj_timezone.now() if is_db_aware else datetime.utcnow()) - timedelta(hours=1)

        logs_data = []
        worker_count = 0
        protected_count = 0
        down_count = 0

        for log in queryset:
            log_serialized = ServerLogSerializer(log).data

            # Classify circuit state
            if log.timestamp and log.timestamp < limit_time:
                status_name = "down"
                down_count += 1
            elif log.min_value <= log.circuit.range_down:
                status_name = "worker"
                worker_count += 1
            else:
                status_name = "protected"
                protected_count += 1

            log_serialized["status_name"] = status_name
            log_serialized["status"] = (status_name == "protected")
            logs_data.append(log_serialized)

        last_added = queryset.order_by("-timestamp").first() if queryset.exists() else None
        last_updated_time = last_added.timestamp if last_added else dj_timezone.now()

        response = {
            'updated': last_updated_time,
            'logs': logs_data,
            'totals': {
                'worker': worker_count,
                'protected': protected_count,
                'down': down_count
            }
        }

        return Response(response, status=status.HTTP_200_OK)

#       #       #       #       #       #       #       #       #       #       #       #

# Sign Up Action
class SignUpView(views.APIView):
    permission_classes = [Visitors]

    def post(self, request):

        # Serializer validation
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get validated data
        name = serializer.validated_data['name']
        username = serializer.validated_data['email']
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Query Authentication
        if User.objects.filter(username=email).exists():

            # Create json response
            response = { 'error' : 'El correo ingresado ya esta registrado' }

            # Send response
            return Response(response, status=status.HTTP_403_FORBIDDEN)
        
        else:

            # Create user data
            user = User.objects.create_user(
                first_name = name,
                username = username,
                email = email,
                password = password
            )
            # Generate token for authentication
            token, _ = Token.objects.get_or_create(user=user)

            # Create json response
            response = {
                'id': user.id,
                'name': user.first_name,
                'token': token
            }

        return Response(SignResponseSerializer(response).data , status=status.HTTP_200_OK)

# Sign In Action
class SignInView(views.APIView):
    permission_classes = [Visitors]

    def post(self, request):

        # Serializer validation
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get validated data
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Query Authentication
        user = authenticate(request, username=email, password=password)

        # Query Authentication
        if user is not None:
            
            login(request, user)

            # Get token
            #token = Token.objects.get(user=user)
            token, _ = Token.objects.get_or_create(user=user)

            # Create json response
            response = {
                'id': user.id,
                'name': user.first_name,
                'token': token
            }

            # Send response
            return Response(SignResponseSerializer(response).data, status=status.HTTP_200_OK)

        else:

            # Create json response
            response = { 'error' : 'User not found' }

            # Send response
            return Response(response, status=status.HTTP_403_FORBIDDEN)

# Logout Action
class LogoutInView(views.APIView):

    def post(self, request):

        logout(request)
        resp = Response({"detail": "Logged out"})

        resp.delete_cookie(
            key='sessionid',
            path='/',
            domain=None
        )

        resp.delete_cookie(
            key='csrftoken',
            path='/',
            domain=None
        )

        return resp