from django.contrib import admin
from .models import Tournament, Participant, Match

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'location', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    list_editable = ['is_active']

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'age', 'gender', 'weight',
                   'age_category', 'weight_category', 'club', 'tournament']
    list_filter = ['gender', 'age_category', 'weight_category', 'tournament']
    search_fields = ['last_name', 'first_name', 'club']
    readonly_fields = ['age_category', 'weight_category', 'source_file', 'row_number']
    list_per_page = 50

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'age_category', 'weight_category', 'round_name', 'status']
    list_filter = ['age_category', 'weight_category', 'status', 'tournament']
    search_fields = ['participant1__last_name', 'participant2__last_name']