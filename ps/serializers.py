from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Station, Session, RateSettings

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'firstname', 'lastname', 'role')
        read_only_fields = ('id',)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('username', 'password', 'firstname', 'lastname', 'role')
        extra_kwargs = {
            'role': {'default': 'player'},
            'firstname': {'required': False},
            'lastname': {'required': False}
        }
    
    def validate_role(self, value):
        if value not in ['player', 'staff', 'admin']:
            raise serializers.ValidationError(_("Le rôle doit être 'player', 'staff' ou 'admin'"))
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            firstname=validated_data.get('firstname', ''),
            lastname=validated_data.get('lastname', ''),
            role=validated_data.get('role', 'player')
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, style={'input_type': 'password'}, write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(request=self.context.get('request'), username=username, password=password)
            
            if not user:
                msg = _('Impossible de se connecter avec les identifiants fournis.')
                raise serializers.ValidationError(msg, code='authorization')
            
            if not user.is_active:
                raise serializers.ValidationError(_('Ce compte a été désactivé.'), code='authorization')
        else:
            msg = _('Veuillez fournir un nom d\'utilisateur et un mot de passe.')
            raise serializers.ValidationError(msg, code='authorization')
        
        refresh = RefreshToken.for_user(user)
        
        return {
            'user': user,
            'token': str(refresh.access_token)
        }


class SessionInfoSerializer(serializers.ModelSerializer):
    player_id = serializers.UUIDField(source='player.id')
    
    class Meta:
        model = Session
        fields = ('player_id', 'start_time')


class SessionSerializer(serializers.ModelSerializer):
    player_id = serializers.UUIDField(source='player.id', read_only=True)
    station_id = serializers.UUIDField(source='station.id', read_only=True)
    
    class Meta:
        model = Session
        fields = ('id', 'player_id', 'station_id', 'start_time', 'end_time', 'duration', 'cost', 'is_active')
        read_only_fields = ('id', 'start_time', 'end_time', 'duration', 'cost', 'is_active')


class SessionCreateSerializer(serializers.Serializer):
    player_id = serializers.UUIDField()
    station_id = serializers.UUIDField()
    
    def validate(self, data):
        player_id = data.get('player_id')
        station_id = data.get('station_id')
        
        # Vérification de l'existence du joueur
        try:
            player = User.objects.get(pk=player_id)
            if player.role != 'player':
                raise serializers.ValidationError(_("L'utilisateur spécifié n'est pas un joueur"))
        except User.DoesNotExist:
            raise serializers.ValidationError(_("Joueur non trouvé"))
        
        # Vérification de l'existence et de la disponibilité de la station
        try:
            station = Station.objects.get(pk=station_id)
            if station.status != 'available':
                raise serializers.ValidationError(_("La station n'est pas disponible"))
        except Station.DoesNotExist:
            raise serializers.ValidationError(_("Station non trouvée"))
        
        # Vérifier si le joueur a déjà une session active
        if Session.objects.filter(player_id=player_id, is_active=True).exists():
            raise serializers.ValidationError(_("Le joueur a déjà une session active"))
        
        data['player'] = player
        data['station'] = station
        return data
    
    def create(self, validated_data):
        player = validated_data.pop('player')
        station = validated_data.pop('station')
        
        # Créer la session
        session = Session.objects.create(
            player=player,
            station=station
        )
        
        # Mettre à jour le statut de la station
        station.status = 'in_use'
        station.current_session = session
        station.save()
        
        return session


class StationSerializer(serializers.ModelSerializer):
    current_session = SessionInfoSerializer(read_only=True)
    
    class Meta:
        model = Station
        fields = ('id', 'name', 'type', 'status', 'current_session')
        read_only_fields = ('id', 'current_session')
    
    def validate_type(self, value):
        if value not in dict(Station.TYPE_CHOICES).keys():
            raise serializers.ValidationError(_("Le type doit être 'PC' ou 'console'"))
        return value
    
    def validate_status(self, value):
        if value not in dict(Station.STATUS_CHOICES).keys():
            raise serializers.ValidationError(_("Le statut doit être 'available', 'in_use' ou 'maintenance'"))
        return value


class RateSettingsSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = RateSettings
        fields = ('id', 'hourly_rate', 'station_type', 'description', 'created_by', 
                  'created_by_username', 'created_at', 'updated_at', 'is_active')
        read_only_fields = ('id', 'created_by', 'created_by_username', 'created_at', 'updated_at')
    
    def validate_hourly_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Le tarif horaire doit être supérieur à zéro"))
        return value
    
    def validate_station_type(self, value):
        if value not in dict(RateSettings.STATION_TYPE_CHOICES).keys():
            raise serializers.ValidationError(_("Le type de station doit être 'PC', 'console' ou 'all'"))
        return value
    
    def create(self, validated_data):
        # Récupérer l'utilisateur qui crée le tarif
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        
        return super().create(validated_data)
