import io

from django.contrib.auth.hashers import make_password
from django.db.models.aggregates import Count, Sum
from django.db.models.expressions import Exists, OuterRef, Value
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, api_view
from rest_framework.permissions import (
    SAFE_METHODS, AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAdminOrReadOnly
from recipes.models import (
    Favorites, Ingredient, Recipe, ShoppingCart, Tag
)
from users.models import Follow, User, SUBSCRIBE_TO_YOURSELF
from .serializers import (
    IngredientSerializer, RecipeReadSerializer, RecipeWriteSerializer,
    FollowRecipeSerializer, FollowSerializer, TagSerializer, TokenSerializer,
    UserCreateSerializer, UserListSerializer, UserPasswordSerializer
)

FILENAME = 'shopping_cart.pdf'
NON_UNIQUE_SUBSCRIBE = 'Вы уже подписаны на данного автора'
EMPTY_SHOPPING_CART = 'Корзина пуста'
SUCCESSFULLY_PASSWORD_CHANGED = 'Пароль изменен'
WRONG_PASSWORD = 'Введены неверные данные для пароля'


class GetObjectMixin:
    serializer_class = FollowRecipeSerializer
    permission_classes = (AllowAny,)

    def get_object(self):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe


class PermissionAndPaginationMixin:

    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class AddDeleteFollow(
    generics.RetrieveDestroyAPIView,
    generics.ListCreateAPIView
):

    serializer_class = FollowSerializer

    def get_queryset(self):
        return self.request.user.follower.select_related(
            'following'
        ).prefetch_related(
            'following__recipe'
        ).annotate(
            recipes_count=Count('following__recipe'),
            is_followed=Value(True),
        )

    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id)
        self.check_object_permissions(self.request, user)
        return user

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.id == instance.id:
            return Response(
                {'errors': SUBSCRIBE_TO_YOURSELF},
                status=status.HTTP_400_BAD_REQUEST)
        if request.user.follower.filter(author=instance).exists():
            return Response(
                {'errors': NON_UNIQUE_SUBSCRIBE},
                status=status.HTTP_400_BAD_REQUEST
            )
        subs = request.user.follower.create(author=instance)
        serializer = self.get_serializer(subs)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.follower.filter(author=instance).delete()


class AddDeleteFavorites(
    GetObjectMixin,
    generics.RetrieveDestroyAPIView,
    generics.ListCreateAPIView
):

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        request.user.favorites.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.favorites.recipe.remove(instance)


class AddDeleteShoppingCart(
    GetObjectMixin,
    generics.RetrieveDestroyAPIView,
    generics.ListCreateAPIView
):

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        request.user.shopping_cart.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.shopping_cart.recipe.remove(instance)


class AuthToken(ObtainAuthToken):

    serializer_class = TokenSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {'auth_token': token.key},
            status=status.HTTP_201_CREATED
        )


class UsersViewSet(UserViewSet):

    serializer_class = UserListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return User.objects.annotate(
            is_followed=Exists(
                self.request.user.follower.filter(
                    author=OuterRef('id'))
            )
        ).prefetch_related(
            'follower', 'following'
        ) if self.request.user.is_authenticated else User.objects.annotate(
            is_followed=Value(False)
        )

    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return UserCreateSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        password = make_password(self.request.data['password'])
        serializer.save(password=password)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        user = request.user
        queryset = Follow.objects.filter(user=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class RecipesViewSet(viewsets.ModelViewSet):

    queryset = Recipe.objects.all()
    filterset_class = RecipeFilter
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_queryset(self):
        return Recipe.objects.annotate(
            is_favorited=Exists(
                Favorites.objects.filter(
                    user=self.request.user, recipe=OuterRef('id'))
            ),
            is_in_shopping_cart=Exists(
                ShoppingCart.objects.filter(
                    user=self.request.user,
                    recipe=OuterRef('id'))
            )
        ).select_related('author').prefetch_related(
            'tags', 'ingredients', 'recipe',
            'shopping_cart', 'favorite_recipe'
        ) if self.request.user.is_authenticated else Recipe.objects.annotate(
            is_in_shopping_cart=Value(False),
            is_favorited=Value(False),
        ).select_related('author').prefetch_related(
            'tags', 'ingredients', 'recipe',
            'shopping_cart', 'favorites'
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        buffer = io.BytesIO()
        page = canvas.Canvas(buffer)
        pdfmetrics.registerFont(TTFont('Montserrat', 'Montserrat-Regular.ttf'))
        x_pos, y_pos = 50, 800
        shopping_cart = (
            request.user.shopping_cart.recipe.values(
                'ingredients__name',
                'ingredients__measurement_unit'
            ).annotate(amount=Sum('recipe__amount')).order_by())
        page.setFont('Montserrat', 14)
        if shopping_cart:
            indent = 20
            page.drawString(x_pos, y_pos, 'Cписок покупок:')
            for index, recipe in enumerate(shopping_cart, start=1):
                page.drawString(
                    x_pos, y_pos - indent,
                    f'{index}. {recipe["ingredients__name"]} - '
                    f'{recipe["amount"]} '
                    f'{recipe["ingredients__measurement_unit"]}.')
                y_pos -= 15
                if y_pos <= 50:
                    page.showPage()
                    y_pos = 800
            page.save()
            buffer.seek(0)
            return FileResponse(buffer, as_attachment=True, filename=FILENAME)
        page.setFont('Vera', 24)
        page.drawString(x_pos, y_pos, EMPTY_SHOPPING_CART)
        page.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=FILENAME)


class TagsViewSet(
    PermissionAndPaginationMixin,
    viewsets.ModelViewSet
):

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientsViewSet(
    PermissionAndPaginationMixin,
    viewsets.ModelViewSet
):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter


@api_view(['post'])
def set_password(request):
    serializer = UserPasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': SUCCESSFULLY_PASSWORD_CHANGED},
            status=status.HTTP_201_CREATED)

    return Response(
        {'error': WRONG_PASSWORD},
        status=status.HTTP_400_BAD_REQUEST
    )
