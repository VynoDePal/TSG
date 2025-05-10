from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
import uuid
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError(_('Le nom d\'utilisateur est obligatoire'))
        
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Un superuser doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Un superuser doit avoir is_superuser=True.'))
        
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('player', 'Joueur'),
        ('staff', 'Personnel'),
        ('admin', 'Administrateur'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    firstname = models.CharField(max_length=100, blank=True)
    lastname = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='player')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['role']
    
    class Meta:
        verbose_name = _('utilisateur')
        verbose_name_plural = _('utilisateurs')
    
    def __str__(self):
        if self.firstname and self.lastname:
            return f"{self.firstname} {self.lastname} ({self.username})"
        return self.username


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    station = models.ForeignKey('Station', on_delete=models.CASCADE, related_name='station_sessions', null=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True, help_text=_('Durée en minutes'))
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('session')
        verbose_name_plural = _('sessions')
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Session {self.id} - {self.player.username}"
    
    def calculate_duration(self):
        """Calcule la durée de la session en minutes"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 60)
        return None
    
    def calculate_cost(self):
        """Calcule le coût de la session en fonction de sa durée"""
        if self.duration:
            # Récupérer le tarif horaire applicable
            if self.station:
                hourly_rate = RateSettings.get_rate_for_station(self.station.type)
            else:
                # Utiliser le tarif par défaut si aucune station n'est associée
                hourly_rate = RateSettings.get_rate_for_station('all')
            
            # Coût = tarif horaire * (durée en minutes / 60)
            return round(float(hourly_rate) * (self.duration / 60), 2)
        return None
    
    def end_session(self):
        """Termine la session et calcule la durée et le coût"""
        from django.utils import timezone
        
        if self.is_active:
            self.end_time = timezone.now()
            self.is_active = False
            self.duration = self.calculate_duration()
            self.cost = self.calculate_cost()
            
            # Mettre à jour le statut de la station
            if self.station:
                self.station.status = 'available'
                self.station.current_session = None
                self.station.save()
            
            self.save()
        
        return self


class Station(models.Model):
    TYPE_CHOICES = (
        ('console', 'Console'),
        ('PC', 'PC'),
    )
    
    STATUS_CHOICES = (
        ('available', 'Disponible'),
        ('in_use', 'En utilisation'),
        ('maintenance', 'En maintenance'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_session = models.OneToOneField(
        Session, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='current_station'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('station')
        verbose_name_plural = _('stations')
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - {self.get_status_display()}"


class RateSettings(models.Model):
    """Modèle pour stocker les paramètres tarifaires du centre de jeux"""
    
    STATION_TYPE_CHOICES = (
        ('console', 'Console'),
        ('PC', 'PC'),
        ('all', 'Tous les types'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=500.0,
        help_text=_('Tarif horaire en FCFA')
    )
    station_type = models.CharField(
        max_length=20, 
        choices=STATION_TYPE_CHOICES, 
        default='all',
        help_text=_('Type de station auquel ce tarif s\'applique')
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_rates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('paramètre tarifaire')
        verbose_name_plural = _('paramètres tarifaires')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Tarif: {self.hourly_rate} FCFA/h pour {self.get_station_type_display()}"
    
    @classmethod
    def get_rate_for_station(cls, station_type):
        """Récupère le tarif horaire applicable pour un type de station donné"""
        # Essayer d'abord de trouver un tarif spécifique pour ce type de station
        specific_rate = cls.objects.filter(station_type=station_type, is_active=True).first()
        if specific_rate:
            return specific_rate.hourly_rate
        
        # Sinon, utiliser le tarif par défaut pour tous les types
        default_rate = cls.objects.filter(station_type='all', is_active=True).first()
        if default_rate:
            return default_rate.hourly_rate
        
        # Si aucun tarif n'est défini, retourner une valeur par défaut
        return 500.0  # 500 FCFA par défaut
