import csv
import io

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.db.models import OuterRef, Subquery
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
        start = request.query_params.get("start")
        end = request.query_params.get("end")
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

        # Create date start range filter
        if start:
            try:
                start_date = parse_date(start) or parse_datetime(start)
                if start_date:
                    logs = logs.filter(timestamp__gte=start_date)
            except Exception:
                pass

        # Create date end range filter
        if end:
            try:
                end_date = parse_date(end) or parse_datetime(end)
                if end_date:
                    logs = logs.filter(timestamp__lte=end_date)
            except Exception:
                pass

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
        circuit = CircuitSerializer(circuit)
        logs = ServerLogChartSerializer(logs, many=True)

        response = {
            "groups" : groups.data,
            "circuit" : circuit.data,
            "logs" : logs.data
        }

        print( response )

        return Response(response, status=status.HTTP_200_OK)

#       #       #       #       #       #       #       #       #       #       #       #

# Last source created
class LastLogPerSourceView(APIView):

    def get_backup(self, request):
        latest_log_subquery = (
            ServerLog.objects
            .filter(
                source_host=OuterRef("source_host"),
                circuit=OuterRef("circuit")
            )
            .order_by("-timestamp")
        )

        # Consulta principal: selecciona el registro más reciente de cada par
        queryset = (
            ServerLog.objects
            .filter(pk=Subquery(latest_log_subquery.values("pk")[:1]))
            .select_related("circuit")  # optimiza el acceso a circuit
            .order_by("source_host", "circuit__target_host")
        )

        serializer = ServerLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def get(self, request):
        today = timezone.now().date()

        latest_log_subquery = (
            ServerLog.objects
            .filter(
                source_host=OuterRef("source_host"),
                circuit=OuterRef("circuit"),
                timestamp__date__gte=today
            )
            .order_by("-timestamp")
        )

        queryset = (
            ServerLog.objects
            .filter(
                pk=Subquery(latest_log_subquery.values("pk")[:1]),
                timestamp__date__gte=today
            )
            .select_related("circuit")
            .order_by("source_host", "circuit__target_host")
        )

        serializer = ServerLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
            token = Token.objects.get(user=user)

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