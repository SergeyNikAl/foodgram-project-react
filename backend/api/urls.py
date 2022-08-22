from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    AddDeleteFollow,
    AddDeleteFavorites,
    AddDeleteShoppingCart,
    AuthToken,
    IngredientsViewSet,
    RecipesViewSet,
    TagsViewSet,
    UsersViewSet,
    set_password
)

app_name = 'api'

router_v1 = DefaultRouter()
router_v1.register('users', UsersViewSet)
router_v1.register('tags', TagsViewSet)
router_v1.register('ingredients', IngredientsViewSet)
router_v1.register('recipes', RecipesViewSet)


urlpatterns = [
     path(
          'auth/token/login/',
          AuthToken.as_view(),
          name='login'
     ),
     path(
          'users/set_password/',
          set_password,
          name='set_password'
     ),
     path(
          'users/<int:user_id>/subscribe/',
          AddDeleteFollow.as_view(),
          name='subscribe'
     ),
     path(
          'recipes/<int:recipe_id>/favorite/',
          AddDeleteFavorites.as_view(),
          name='favorite_recipe'
     ),
     path(
          'recipes/<int:recipe_id>/shopping_cart/',
          AddDeleteShoppingCart.as_view(),
          name='shopping_cart'
     ),
     path('', include(router_v1.urls)),
     path('', include('djoser.urls')),
     path('auth/', include('djoser.urls.authtoken')),
]
