from django.contrib import admin

from .models import Character, Game, Location


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'ambiance', 'owner', 'created_at')
    search_fields = ('title', 'keywords')
    list_filter = ('genre', 'ambiance', 'created_at')

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'game')
    search_fields = ('name', 'role')
    list_filter = ('game',)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'game')
    search_fields = ('name',)
    list_filter = ('game',)
