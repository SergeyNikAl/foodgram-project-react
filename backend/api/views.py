import io

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.expressions import Exists, OuterRef
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
from .serializers import (
    FavoriteRecipeSerializer,
    FollowSerializer,
    IngredientSerializer,
    ListUserSerializer,
    RecipesCreateSerializer,
    RecipesListSerializer,
    TagSerializer,
)
from users.models import Follow, User
from recipes.models import (
    Favorites,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag,
)

FILENAME = 'shopping_cart.pdf'
SUBSCRIBE_TO_YOURSELF = 'Нельзя подписаться на самого себя'
NO_SUBSCRIPTION = 'Нельзя отписаться от автора, на которго вы не подписаны'
MISSING_RECIPE = 'Рецепт отсутсвует'


class UsersViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = ListUserSerializer

    @action(
        methods=["GET"], detail=False, permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        user = self.request.user
        queryset = Follow.objects.filter(user=user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=["POST", "DELETE"],
        detail=True,
    )
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)
        if request.method == "POST":
            if request.user.id == author.id:
                raise ValidationError(SUBSCRIBE_TO_YOURSELF)
            else:
                serializer = FollowSerializer(
                    Follow.objects.create(user=request.user, author=author),
                    context={"request": request},
                )
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED
                )
        elif request.method == "DELETE":
            if Follow.objects.filter(
                    user=request.user, author=author
            ).exists():
                Follow.objects.filter(
                    user=request.user, author=author
                ).delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"errors": NO_SUBSCRIPTION},
                    status=status.HTTP_400_BAD_REQUEST,
                )


class IngredientsViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter


class TagsViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = TagSerializer


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filterset_class = RecipeFilter
    permission_classes = (IsOwnerOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipesListSerializer
        return RecipesCreateSerializer

    def get_queryset(self):
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "tags",
            "ingredients",
            "recipe",
            "shopping_cart",
            "favorite_recipe",
        )
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_favorite=Exists(
                    Favorites.objects.filter(
                        user=self.request.user, recipe=OuterRef("id")
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=self.request.user, recipe=OuterRef("id")
                    )
                ),
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        methods=["POST", "DELETE"],
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def favorites(self, request, pk):
        recipe_pk = self.kwargs.get("pk")
        recipe = get_object_or_404(Recipe, pk=recipe_pk)
        if request.method == "POST":
            serializer = FavoriteRecipeSerializer(recipe)
            Favorites.objects.create(
                user=self.request.user, recipe=recipe
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == "DELETE":
            if Favorites.objects.filter(
                    user=self.request.user, recipe=recipe
            ).exists():
                Favorites.objects.get(
                    user=self.request.user, recipe=recipe
                ).delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"errors": MISSING_RECIPE},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(
        methods=["POST", "DELETE"],
        detail=True,
    )
    def shopping_cart(self, request, pk):
        recipe_pk = self.kwargs.get("pk")
        recipe = get_object_or_404(Recipe, pk=recipe_pk)
        if request.method == "POST":
            serializer = FavoriteRecipeSerializer(recipe)
            ShoppingCart.objects.create(user=self.request.user, recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == "DELETE":
            if ShoppingCart.objects.filter(
                    user=self.request.user, recipe=recipe
            ).exists():
                ShoppingCart.objects.get(
                    user=self.request.user, recipe=recipe
                ).delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"errors": MISSING_RECIPE},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(
        detail=False,
        methods=['GET'],
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
        page.setFont('Montserrat', 24)
        page.drawString(x_pos, y_pos, MISSING_RECIPE)
        page.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=FILENAME)
