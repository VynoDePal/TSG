from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions personnalisé qui retourne des réponses JSON appropriées.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        error_data = {
            'error': response.data
        }
        response.data = error_data
    
    return response


class ErrorResponse:
    """Utilitaire pour générer des réponses d'erreur standardisées"""
    
    @staticmethod
    def bad_request(message="Requête invalide"):
        return JsonResponse({'error': message}, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def unauthorized(message="Non autorisé"):
        return JsonResponse({'error': message}, status=status.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def not_found(message="Ressource non trouvée"):
        """Retourne une réponse d'erreur 404 Not Found"""
        return ErrorResponse._make_error_response(status.HTTP_404_NOT_FOUND, message)
    
    @staticmethod
    def forbidden(message="Accès interdit"):
        return JsonResponse({'error': message}, status=status.HTTP_403_FORBIDDEN)
    
    @staticmethod
    def not_found(message="Ressource non trouvée"):
        return JsonResponse({'error': message}, status=status.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def conflict(message="Conflit avec l'état actuel de la ressource"):
        return JsonResponse({'error': message}, status=status.HTTP_409_CONFLICT)
    
    @staticmethod
    def server_error(message="Erreur interne du serveur"):
        return JsonResponse({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CostCalculator:
    """Utilitaire pour calculer les coûts des sessions"""
    
    @staticmethod
    def calculate_session_cost(duration_minutes):
        """
        Calcule le coût d'une session en fonction de sa durée
        
        Args:
            duration_minutes (int): Durée de la session en minutes
            
        Returns:
            float: Coût calculé de la session
        """
        # Prix de base par heure
        base_hourly_rate = 10.0
        
        # Convertir la durée en heures
        hours = duration_minutes / 60
        
        # Appliquer le tarif horaire
        cost = base_hourly_rate * hours
        
        # Arrondir à 2 décimales
        return round(cost, 2)
    @staticmethod
    def bad_request(message="Requête invalide"):
        return JsonResponse({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def server_error(message="Erreur interne du serveur"):
        return JsonResponse({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
