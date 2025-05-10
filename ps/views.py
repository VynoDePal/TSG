from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Avg
from django.views.generic import View
from datetime import datetime
import json
from .models import Station, Session, RateSettings
from django.db import models
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    StationSerializer, SessionSerializer, SessionCreateSerializer,
    RateSettingsSerializer
)
from .utils import ErrorResponse
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import get_user_model

User = get_user_model()
from drf_yasg import openapi

User = get_user_model()


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=LoginSerializer,
        operation_description="Authentifie un utilisateur et retourne un jeton JWT",
        responses={
            200: openapi.Response(
                description="Authentification réussie",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'role': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    }
                )
            ),
            400: "Données invalides",
            401: "Authentification échouée"
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token = serializer.validated_data['token']
            user_serializer = UserSerializer(user)
            
            return JsonResponse({
                'token': token,
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        
        return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=RegisterSerializer,
        operation_description="Crée un nouveau compte joueur",
        responses={
            201: UserSerializer,
            400: "Données invalides"
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user).data
            return JsonResponse(user_data, status=status.HTTP_201_CREATED, safe=False)
        
        return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class StationListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Liste toutes les stations avec leur statut",
        responses={
            200: StationSerializer(many=True),
            401: "Non autorisé"
        }
    )
    def get(self, request):
        stations = Station.objects.all()
        serializer = StationSerializer(stations, many=True)
        return JsonResponse(serializer.data, safe=False, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=StationSerializer,
        operation_description="Crée une nouvelle station",
        responses={
            201: StationSerializer,
            400: "Données invalides",
            401: "Non autorisé"
        }
    )
    def post(self, request):
        # Vérifiez si l'utilisateur est un administrateur ou un membre du personnel
        if request.user.role not in ['admin', 'staff']:
            return ErrorResponse.forbidden("Seuls les administrateurs et le personnel peuvent créer des stations")
        
        serializer = StationSerializer(data=request.data)
        if serializer.is_valid():
            station = serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        
        return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class StationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupère les détails d'une station spécifique",
        responses={
            200: StationSerializer,
            401: "Non autorisé",
            404: "Station non trouvée"
        }
    )
    def get(self, request, station_id):
        try:
            station = Station.objects.get(pk=station_id)
            serializer = StationSerializer(station)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        except Station.DoesNotExist:
            return ErrorResponse.not_found("Station non trouvée")
    
    @swagger_auto_schema(
        request_body=StationSerializer,
        operation_description="Met à jour les détails d'une station",
        responses={
            200: StationSerializer,
            400: "Données invalides",
            401: "Non autorisé",
            403: "Accès interdit",
            404: "Station non trouvée"
        }
    )
    def put(self, request, station_id):
        # Vérifiez si l'utilisateur est un administrateur ou un membre du personnel
        if request.user.role not in ['admin', 'staff']:
            return ErrorResponse.forbidden("Seuls les administrateurs et le personnel peuvent mettre à jour les stations")
        
        try:
            station = Station.objects.get(pk=station_id)
            serializer = StationSerializer(station, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return JsonResponse(serializer.data, status=status.HTTP_200_OK)
            
            return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Station.DoesNotExist:
            return ErrorResponse.not_found("Station non trouvée")
    
    @swagger_auto_schema(
        operation_description="Supprime une station",
        responses={
            204: "Suppression réussie",
            401: "Non autorisé",
            403: "Accès interdit",
            404: "Station non trouvée"
        }
    )
    def delete(self, request, station_id):
        # Vérifiez si l'utilisateur est un administrateur
        if request.user.role != 'admin':
            return ErrorResponse.forbidden("Seuls les administrateurs peuvent supprimer des stations")
        
        try:
            station = Station.objects.get(pk=station_id)
            station.delete()
            return JsonResponse({'message': 'Station supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)
        except Station.DoesNotExist:
            return ErrorResponse.not_found("Station non trouvée")


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Liste les sessions avec filtres optionnels (joueur, date)",
        manual_parameters=[
            openapi.Parameter(
                name='player_id',
                in_=openapi.IN_QUERY,
                description='ID du joueur pour filtrer les sessions',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=False
            ),
            openapi.Parameter(
                name='date',
                in_=openapi.IN_QUERY,
                description='Date pour filtrer les sessions (format: YYYY-MM-DD)',
                type=openapi.TYPE_STRING,
                format='date',
                required=False
            )
        ],
        responses={
            200: SessionSerializer(many=True),
            400: "Paramètres de requête invalides",
            401: "Non autorisé"
        }
    )
    def get(self, request):
        # Filtrage par joueur
        player_id = request.query_params.get('player_id')
        date_str = request.query_params.get('date')
        
        filters = Q()
        
        if player_id:
            try:
                # Valider l'UUID
                player = User.objects.get(pk=player_id)
                filters &= Q(player=player)
            except (User.DoesNotExist, ValueError):
                return ErrorResponse.bad_request("ID de joueur invalide")
        
        if date_str:
            try:
                # Convertir la chaîne de date en objet date
                session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                filters &= Q(start_time__date=session_date)
            except ValueError:
                return ErrorResponse.bad_request("Format de date invalide. Utilisez YYYY-MM-DD")
        
        # Limiter les résultats selon le rôle
        if request.user.role == 'player':
            # Les joueurs ne peuvent voir que leurs propres sessions
            filters &= Q(player=request.user)
        
        sessions = Session.objects.filter(filters)
        serializer = SessionSerializer(sessions, many=True)
        
        return JsonResponse(serializer.data, safe=False)
    
    @swagger_auto_schema(
        request_body=SessionCreateSerializer,
        operation_description="Démarre une nouvelle session en assignant un joueur à une station",
        responses={
            201: SessionSerializer,
            400: "Données invalides",
            401: "Non autorisé",
            403: "Accès interdit"
        }
    )
    def post(self, request):
        # Vérifier si l'utilisateur est autorisé à créer des sessions
        if request.user.role not in ['admin', 'staff']:
            return ErrorResponse.forbidden("Seuls les administrateurs et le personnel peuvent créer des sessions")
        
        serializer = SessionCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Créer la session
            session = serializer.save()
            
            # Renvoyer les détails de la session créée
            response_serializer = SessionSerializer(session)
            return JsonResponse(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupère les détails d'une session spécifique",
        responses={
            200: SessionSerializer,
            401: "Non autorisé",
            403: "Accès interdit",
            404: "Session non trouvée"
        }
    )
    def get(self, request, session_id):
        try:
            session = Session.objects.get(pk=session_id)
            
            # Vérifier les autorisations
            if request.user.role == 'player' and request.user != session.player:
                return ErrorResponse.forbidden("Vous n'êtes pas autorisé à voir cette session")
            
            serializer = SessionSerializer(session)
            return JsonResponse(serializer.data)
        
        except Session.DoesNotExist:
            return ErrorResponse.not_found("Session non trouvée")


class EndSessionView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Termine une session, calcule la durée et le coût",
        responses={
            200: SessionSerializer,
            400: "La session est déjà terminée",
            401: "Non autorisé",
            403: "Accès interdit",
            404: "Session non trouvée"
        }
    )
    def put(self, request, session_id):
        # Vérifier si l'utilisateur est autorisé à terminer des sessions
        if request.user.role not in ['admin', 'staff']:
            return ErrorResponse.forbidden("Seuls les administrateurs et le personnel peuvent terminer des sessions")
        
        try:
            session = Session.objects.get(pk=session_id)
            
            # Vérifier si la session est déjà terminée
            if not session.is_active:
                return ErrorResponse.bad_request("Cette session est déjà terminée")
            
            # Terminer la session
            session.end_session()
            
            # Renvoyer les détails mis à jour
            serializer = SessionSerializer(session)
            return JsonResponse(serializer.data)

        except Session.DoesNotExist:
            return ErrorResponse.not_found("Session non trouvée")


class RateSettingsListView(APIView):
    """Vue pour lister et créer des paramètres tarifaires"""
    
    @swagger_auto_schema(
        operation_description="Liste tous les paramètres tarifaires actifs",
        manual_parameters=[
            openapi.Parameter(
                name='station_type',
                in_=openapi.IN_QUERY,
                description='Filtrer par type de station (console, PC, all)',
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: RateSettingsSerializer(many=True),
            500: "Erreur serveur"
        }
    )
    def get(self, request):
        """Retourne tous les tarifs actifs"""
        try:
            # Récupérer tous les tarifs actifs
            queryset = RateSettings.objects.filter(is_active=True)
            
            # Filtrer par type de station si spécifié
            station_type = request.GET.get('station_type', None)
            if station_type:
                queryset = queryset.filter(station_type=station_type)
            
            # Sérialiser les données
            serializer = RateSettingsSerializer(queryset, many=True)
            return JsonResponse(serializer.data, safe=False)
        except Exception as e:
            return ErrorResponse.server_error(str(e))
    
    @swagger_auto_schema(
        request_body=RateSettingsSerializer,
        operation_description="Crée un nouveau paramètre tarifaire (Admin/Staff uniquement)",
        responses={
            201: RateSettingsSerializer,
            400: "Données invalides",
            401: "Non authentifié",
            403: "Permissions insuffisantes",
            500: "Erreur serveur"
        }
    )
    def post(self, request):
        """Crée un nouveau paramètre tarifaire (Admin/Staff uniquement)"""
        try:
            # Vérifier les permissions
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return ErrorResponse.unauthorized("Authentification requise")
            
            if not (request.user.role == 'admin' or request.user.role == 'staff'):
                return ErrorResponse.forbidden("Vous n'avez pas les permissions requises pour cette action")
            
            # Désérialiser et valider les données
            data = json.loads(request.body)
            serializer = RateSettingsSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                # Créer le tarif
                serializer.save(created_by=request.user)
                return JsonResponse(serializer.data, status=201)
            else:
                return ErrorResponse.bad_request(serializer.errors)
        except json.JSONDecodeError:
            return ErrorResponse.bad_request("Format JSON invalide")
        except Exception as e:
            return ErrorResponse.server_error(str(e))


class RateSettingsDetailView(APIView):
    """Vue pour afficher, modifier ou supprimer un paramètre tarifaire"""
    
    def get_object(self, rate_id):
        """Récupère l'objet RateSettings ou lève une exception s'il n'existe pas"""
        try:
            return RateSettings.objects.get(pk=rate_id)
        except RateSettings.DoesNotExist:
            raise Http404("Paramètre tarifaire non trouvé")
    
    @swagger_auto_schema(
        operation_description="Récupère les détails d'un paramètre tarifaire spécifique",
        responses={
            200: RateSettingsSerializer,
            404: "Paramètre tarifaire non trouvé",
            500: "Erreur serveur"
        }
    )
    def get(self, request, rate_id):
        """Récupère les détails d'un paramètre tarifaire"""
        try:
            rate = self.get_object(rate_id)
            serializer = RateSettingsSerializer(rate)
            return JsonResponse(serializer.data)
        except Http404 as e:
            return ErrorResponse.not_found("Paramètre tarifaire non trouvé")
        except Exception as e:
            return ErrorResponse.server_error(str(e))
    
    @swagger_auto_schema(
        request_body=RateSettingsSerializer,
        operation_description="Met à jour un paramètre tarifaire (Admin/Staff uniquement)",
        responses={
            200: RateSettingsSerializer,
            400: "Données invalides",
            403: "Permissions insuffisantes",
            404: "Paramètre tarifaire non trouvé",
            500: "Erreur serveur"
        }
    )
    def put(self, request, rate_id):
        """Met à jour un paramètre tarifaire (Admin/Staff uniquement)"""
        try:
            # Vérifier les permissions
            if not (request.user.role == 'admin' or request.user.role == 'staff'):
                return ErrorResponse.forbidden("Vous n'avez pas les permissions requises pour cette action")
            
            rate = self.get_object(rate_id)
            
            # Désérialiser et valider les données
            data = json.loads(request.body)
            serializer = RateSettingsSerializer(rate, data=data, context={'request': request})
            
            if serializer.is_valid():
                # Mettre à jour le tarif
                serializer.save()
                return JsonResponse(serializer.data)
            else:
                return ErrorResponse.bad_request(serializer.errors)
        except Http404 as e:
            return ErrorResponse.not_found("Paramètre tarifaire non trouvé")
        except json.JSONDecodeError:
            return ErrorResponse.bad_request("Format JSON invalide")
        except Exception as e:
            return ErrorResponse.server_error(str(e))
    
    @swagger_auto_schema(
        operation_description="Désactive un paramètre tarifaire sans le supprimer (Admin uniquement)",
        responses={
            204: "Tarif désactivé avec succès",
            403: "Permissions insuffisantes - réservé aux administrateurs",
            404: "Paramètre tarifaire non trouvé",
            500: "Erreur serveur"
        }
    )
    def delete(self, request, rate_id):
        """Désactive un paramètre tarifaire (Admin uniquement)"""
        try:
            # Vérifier les permissions
            if request.user.role != 'admin':
                return ErrorResponse.forbidden("Seuls les administrateurs peuvent désactiver des tarifs")
            
            rate = self.get_object(rate_id)
            
            # Au lieu de supprimer, on désactive le tarif
            rate.is_active = False
            rate.save()
            
            return HttpResponse(status=204)  # No content
        except Http404 as e:
            return ErrorResponse.not_found("Paramètre tarifaire non trouvé")
        except Exception as e:
            return ErrorResponse.server_error(str(e))


class CurrentRatesView(APIView):
    """Vue pour récupérer les tarifs actuels pour chaque type de station"""
    
    @swagger_auto_schema(
        operation_description="Retourne les tarifs horaires actuels pour chaque type de station",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'console': openapi.Schema(type=openapi.TYPE_NUMBER, description='Tarif horaire pour les consoles (FCFA)'),
                    'PC': openapi.Schema(type=openapi.TYPE_NUMBER, description='Tarif horaire pour les PCs (FCFA)'),
                    'all': openapi.Schema(type=openapi.TYPE_NUMBER, description='Tarif horaire par défaut (FCFA)')
                }
            ),
            401: "Non authentifié",
            500: "Erreur serveur"
        }
    )
    def get(self, request):
        """Retourne les tarifs actuels pour chaque type de station"""
        try:
            # Vérifier l'authentification
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return ErrorResponse.unauthorized("Authentification requise")
            
            # Initialiser le dictionnaire de résultats
            result = {}
            
            # Récupérer les tarifs pour chaque type de station
            for station_type, _ in RateSettings.STATION_TYPE_CHOICES:
                rate = RateSettings.get_rate_for_station(station_type)
                result[station_type] = float(rate)
            
            return JsonResponse(result)
        except Exception as e:
            return ErrorResponse.server_error(str(e))


class RevenueReportView(APIView):
    """Vue pour générer des rapports sur les revenus"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Génère un rapport des revenus pour une période donnée",
        manual_parameters=[
            openapi.Parameter(
                name='start_date',
                in_=openapi.IN_QUERY,
                description='Date de début au format YYYY-MM-DD',
                type=openapi.TYPE_STRING,
                format='date',
                required=True
            ),
            openapi.Parameter(
                name='end_date',
                in_=openapi.IN_QUERY,
                description='Date de fin au format YYYY-MM-DD',
                type=openapi.TYPE_STRING,
                format='date',
                required=True
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_revenue': openapi.Schema(type=openapi.TYPE_NUMBER, description='Revenu total en FCFA'),
                    'details': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                'revenue': openapi.Schema(type=openapi.TYPE_NUMBER)
                            }
                        )
                    )
                }
            ),
            400: "Paramètres de requête invalides",
            401: "Non authentifié",
            403: "Accès interdit"
        }
    )
    def get(self, request):
        """Génère un rapport des revenus pour une période donnée"""
        try:
            # Vérifier les autorisations (seuls les admin et le personnel peuvent voir les rapports financiers)
            if request.user.role not in ['admin', 'staff']:
                return ErrorResponse.forbidden("Seuls les administrateurs et le personnel peuvent accéder aux rapports financiers")
            
            # Récupérer et valider les paramètres de date
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            
            if not start_date_str or not end_date_str:
                return ErrorResponse.bad_request("Les paramètres start_date et end_date sont requis")
            
            try:
                # Convertir les chaînes de date en objets date
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                # Ajouter un jour à end_date pour inclure toute la journée
                end_date_inclusive = end_date + timezone.timedelta(days=1)
            except ValueError:
                return ErrorResponse.bad_request("Format de date invalide. Utilisez YYYY-MM-DD")
            
            # Vérifier que la date de début est avant la date de fin
            if start_date > end_date:
                return ErrorResponse.bad_request("La date de début doit être antérieure à la date de fin")
            
            # Récupérer les sessions terminées dans la période spécifiée
            sessions = Session.objects.filter(
                is_active=False,
                end_time__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time())),
                end_time__lt=timezone.make_aware(datetime.combine(end_date_inclusive, datetime.min.time()))
            )
            
            # Calculer le revenu total
            total_revenue = sum(session.cost or 0 for session in sessions)
            
            # Préparer les détails par jour
            details = []
            current_date = start_date
            while current_date <= end_date:
                # Filtrer les sessions pour la journée courante
                day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                day_end = timezone.make_aware(datetime.combine(current_date + timezone.timedelta(days=1), datetime.min.time()))
                day_sessions = sessions.filter(end_time__gte=day_start, end_time__lt=day_end)
                
                # Calculer le revenu du jour
                day_revenue = sum(session.cost or 0 for session in day_sessions)
                
                details.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'revenue': float(day_revenue)
                })
                
                # Passer au jour suivant
                current_date += timezone.timedelta(days=1)
            
            return JsonResponse({
                'total_revenue': float(total_revenue),
                'details': details
            })
        
        except Exception as e:
            return ErrorResponse.server_error(str(e))


class UsageReportView(APIView):
    """Vue pour générer des rapports sur l'utilisation des stations"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Fournit des statistiques d'utilisation (nombre de sessions, durée moyenne)",
        manual_parameters=[
            openapi.Parameter(
                name='start_date',
                in_=openapi.IN_QUERY,
                description='Date de début au format YYYY-MM-DD',
                type=openapi.TYPE_STRING,
                format='date',
                required=True
            ),
            openapi.Parameter(
                name='end_date',
                in_=openapi.IN_QUERY,
                description='Date de fin au format YYYY-MM-DD',
                type=openapi.TYPE_STRING,
                format='date',
                required=True
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_sessions': openapi.Schema(type=openapi.TYPE_INTEGER, description='Nombre total de sessions'),
                    'average_duration': openapi.Schema(type=openapi.TYPE_NUMBER, description='Durée moyenne des sessions en minutes'),
                    'details': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                'sessions_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'average_duration': openapi.Schema(type=openapi.TYPE_NUMBER)
                            }
                        )
                    )
                }
            ),
            400: "Paramètres de requête invalides",
            401: "Non authentifié",
            403: "Accès interdit"
        }
    )
    def get(self, request):
        """Fournit des statistiques d'utilisation (nombre de sessions, durée moyenne)"""
        try:
            # Vérifier les autorisations (seuls les admin et le personnel peuvent voir les rapports)
            if request.user.role not in ['admin', 'staff']:
                return ErrorResponse.forbidden("Seuls les administrateurs et le personnel peuvent accéder aux rapports d'utilisation")
            
            # Récupérer et valider les paramètres de date
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            
            if not start_date_str or not end_date_str:
                return ErrorResponse.bad_request("Les paramètres start_date et end_date sont requis")
            
            try:
                # Convertir les chaînes de date en objets date
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                # Ajouter un jour à end_date pour inclure toute la journée
                end_date_inclusive = end_date + timezone.timedelta(days=1)
            except ValueError:
                return ErrorResponse.bad_request("Format de date invalide. Utilisez YYYY-MM-DD")
            
            # Vérifier que la date de début est avant la date de fin
            if start_date > end_date:
                return ErrorResponse.bad_request("La date de début doit être antérieure à la date de fin")
            
            # Récupérer les sessions terminées dans la période spécifiée
            sessions = Session.objects.filter(
                is_active=False,
                end_time__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time())),
                end_time__lt=timezone.make_aware(datetime.combine(end_date_inclusive, datetime.min.time()))
            )
            
            # Calculer les statistiques globales
            total_sessions = sessions.count()
            
            # Éviter la division par zéro
            if total_sessions > 0:
                # Utiliser l'agrégation pour calculer la durée moyenne
                avg_duration = sessions.aggregate(avg_duration=models.Avg('duration'))['avg_duration'] or 0
            else:
                avg_duration = 0
            
            # Préparer les détails par jour
            details = []
            current_date = start_date
            while current_date <= end_date:
                # Filtrer les sessions pour la journée courante
                day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                day_end = timezone.make_aware(datetime.combine(current_date + timezone.timedelta(days=1), datetime.min.time()))
                day_sessions = sessions.filter(end_time__gte=day_start, end_time__lt=day_end)
                
                # Calculer les statistiques du jour
                day_count = day_sessions.count()
                
                if day_count > 0:
                    day_avg_duration = day_sessions.aggregate(avg_duration=models.Avg('duration'))['avg_duration'] or 0
                else:
                    day_avg_duration = 0
                
                details.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'sessions_count': day_count,
                    'average_duration': round(float(day_avg_duration), 2)
                })
                
                # Passer au jour suivant
                current_date += timezone.timedelta(days=1)
            
            return JsonResponse({
                'total_sessions': total_sessions,
                'average_duration': round(float(avg_duration), 2),
                'details': details
            })
        
        except Exception as e:
            return ErrorResponse.server_error(str(e))


class UserListView(APIView):
    """Vue pour lister tous les utilisateurs (réservée aux administrateurs)"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Liste tous les utilisateurs (administrateurs uniquement)",
        responses={
            200: openapi.Response(
                description="Liste des utilisateurs",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'role': openapi.Schema(type=openapi.TYPE_STRING, enum=['player', 'staff', 'admin'])
                        }
                    )
                )
            ),
            401: "Non authentifié",
            403: "Accès interdit"
        }
    )
    def get(self, request):
        """Liste tous les utilisateurs (administrateurs uniquement)"""
        try:
            # Vérifier que l'utilisateur est un administrateur
            if request.user.role != 'admin':
                return ErrorResponse.forbidden("Seuls les administrateurs peuvent accéder à la liste des utilisateurs")
            
            # Récupérer tous les utilisateurs
            users = User.objects.all()
            
            # Sérialiser les données
            serializer = UserSerializer(users, many=True)
            
            return JsonResponse(serializer.data, safe=False)
        
        except Exception as e:
            return ErrorResponse.server_error(str(e))


class UserDetailView(APIView):
    """Vue pour récupérer, mettre à jour ou supprimer un utilisateur spécifique"""
    permission_classes = [IsAuthenticated]
    
    def get_user(self, user_id):
        """Récupère un utilisateur par son ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Récupère les détails d'un utilisateur",
        responses={
            200: UserSerializer(),
            401: "Non authentifié",
            403: "Accès interdit",
            404: "Utilisateur non trouvé"
        }
    )
    def get(self, request, user_id):
        """Récupère les détails d'un utilisateur"""
        try:
            # Vérifier que l'utilisateur est un administrateur ou l'utilisateur lui-même
            if request.user.role != 'admin' and str(request.user.id) != str(user_id):
                return ErrorResponse.forbidden("Seuls les administrateurs ou l'utilisateur lui-même peuvent accéder à ces informations")
            
            # Récupérer l'utilisateur
            user = self.get_user(user_id)
            if not user:
                return ErrorResponse.not_found("Utilisateur non trouvé")
            
            # Sérialiser et retourner les données
            serializer = UserSerializer(user)
            return JsonResponse(serializer.data)
        
        except Exception as e:
            return ErrorResponse.server_error(str(e))
    
    @swagger_auto_schema(
        operation_description="Met à jour les informations d'un utilisateur",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
                'role': openapi.Schema(type=openapi.TYPE_STRING, enum=['player', 'staff', 'admin'])
            }
        ),
        responses={
            200: UserSerializer(),
            400: "Données invalides",
            401: "Non authentifié",
            403: "Accès interdit",
            404: "Utilisateur non trouvé"
        }
    )
    def put(self, request, user_id):
        """Met à jour un utilisateur (par exemple, rôle ou mot de passe)"""
        try:
            # Vérifier que l'utilisateur est un administrateur ou l'utilisateur lui-même
            if request.user.role != 'admin' and str(request.user.id) != str(user_id):
                return ErrorResponse.forbidden("Seuls les administrateurs ou l'utilisateur lui-même peuvent modifier ces informations")
            
            # Si l'utilisateur est en train de modifier son propre rôle et n'est pas admin, refuser
            if str(request.user.id) == str(user_id) and request.user.role != 'admin' and 'role' in request.data:
                return ErrorResponse.forbidden("Seuls les administrateurs peuvent modifier les rôles")
            
            # Récupérer l'utilisateur
            user = self.get_user(user_id)
            if not user:
                return ErrorResponse.not_found("Utilisateur non trouvé")
            
            # Récupérer les données de la requête
            data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
            
            # Mettre à jour le nom d'utilisateur si fourni
            if 'username' in data:
                # Vérifier que le nom d'utilisateur n'est pas déjà pris
                if User.objects.filter(username=data['username']).exclude(pk=user_id).exists():
                    return ErrorResponse.bad_request("Ce nom d'utilisateur est déjà utilisé")
                user.username = data['username']
            
            # Mettre à jour le mot de passe si fourni
            if 'password' in data and data['password']:
                user.set_password(data['password'])
            
            # Mettre à jour le rôle si fourni et si l'utilisateur est un administrateur
            if 'role' in data and request.user.role == 'admin':
                if data['role'] not in dict(User.ROLE_CHOICES).keys():
                    return ErrorResponse.bad_request("Rôle invalide")
                user.role = data['role']
            
            # Sauvegarder les modifications
            user.save()
            
            # Sérialiser et retourner les données
            serializer = UserSerializer(user)
            return JsonResponse(serializer.data)
        
        except Exception as e:
            return ErrorResponse.server_error(str(e))
    
    @swagger_auto_schema(
        operation_description="Supprime un utilisateur",
        responses={
            204: "Utilisateur supprimé avec succès",
            401: "Non authentifié",
            403: "Accès interdit",
            404: "Utilisateur non trouvé"
        }
    )
    def delete(self, request, user_id):
        """Supprime un utilisateur"""
        try:
            # Vérifier que l'utilisateur est un administrateur
            if request.user.role != 'admin':
                return ErrorResponse.forbidden("Seuls les administrateurs peuvent supprimer des utilisateurs")
            
            # Récupérer l'utilisateur
            user = self.get_user(user_id)
            if not user:
                return ErrorResponse.not_found("Utilisateur non trouvé")
            
            # Empêcher la suppression du propre compte de l'administrateur
            if str(request.user.id) == str(user_id):
                return ErrorResponse.bad_request("Vous ne pouvez pas supprimer votre propre compte")
            
            # Supprimer l'utilisateur
            user.delete()
            
            # Retourner une réponse 204 No Content
            return Response(status=204)
        
        except Exception as e:
            return ErrorResponse.server_error(str(e))
