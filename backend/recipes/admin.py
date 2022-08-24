from django.contrib import admin

from .models import (
    Favorites, Ingredient, RecipeIngredients, Recipe, Tag, ShoppingCart
)

EMPTY_VALUE = '-пусто-'


class RecipeIngredientsAdmin(admin.StackedInline):
    model = RecipeIngredients
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'get_author', 'name', 'text',
        'cooking_time', 'get_tags', 'pub_date', 'get_favorite_count'
    )
    search_fields = (
        'name', 'cooking_time',
        'author__username', 'ingredients__name'
    )
    list_filter = ('pub_date', 'tags',)
    inlines = (RecipeIngredientsAdmin,)
    empty_value_display = EMPTY_VALUE

    @admin.display(description='Ник пользователя')
    def get_author(self, obj):
        return obj.author.username

    @admin.display(description='Тэги')
    def get_tags(self, obj):
        data = [tag.name for tag in obj.tags.all()]
        return ', '.join(data)

    @admin.display(description='В избранном')
    def get_favorite_count(self, obj):
        return obj.favorite_recipe.count()


@admin.register(Favorites)
class FavoritesAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'get_count')
    empty_value_display = EMPTY_VALUE

    @admin.display(description='В избранных')
    def get_count(self, obj):
        return obj.recipe.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit',)
    search_fields = ('name',)
    empty_value_display = EMPTY_VALUE


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color', 'slug',)
    search_fields = ('name', 'slug',)
    empty_value_display = EMPTY_VALUE


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_count')
    empty_value_display = EMPTY_VALUE

    @admin.display(description='В корзине')
    def get_count(self, obj):
        return obj.recipe.count()
