import re

from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from pprint import pprint

from recipes.models import (
    AMOUNT_OF_INGREDIENTS,
    COCKING_TIME_MESSAGE,
    AmountIngredient,
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag
)
from users.models import Follow, User

USERNAME_SYMBOLS = re.compile(r'[\w.@+-@./+-]+')
INVALID_USERNAME_SYMBOLS = 'Недопустимые символы: {value}'
ERROR_TAGS_FOR_INGREDIENT = 'Необходимо заполнить хотя бы один тэг для рецепта'
ERROR_UNIQUE_INGREDIENT = 'Ингредиент(ы) "{value}" уже добавлен(ы) в рецепт'


class CreateUserSerializer(UserCreateSerializer):
    """
    Сериализатор для регистрации пользователей.
    """

    class Meta:
        model = User
        fields = (
            'email', 'password', 'username', 'first_name', 'last_name',
        )
        extra_kwargs = {'password': {'write_only': True}}


class ListUserSerializer(UserSerializer):
    """
    Сериализатор для управления пользователями.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return Follow.objects.filter(
            user=user, author=obj
        ).exists() if user.is_authenticated else False


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для тэгов.
    """

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиентов.
    """

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class IngredientCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления ингредиентов при создании рецепта.
    """
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = AmountIngredient
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError(AMOUNT_OF_INGREDIENTS)
        return value


class ReadIngredientsRecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для просмотра ингредиентов в рецепте.
    """
    id = serializers.ReadOnlyField(source='ingredients.id')
    name = serializers.ReadOnlyField(source='ingredients.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredients.measurement_unit'
    )

    class Meta:
        model = AmountIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)
        validators = [UniqueTogetherValidator(
            queryset=AmountIngredient.objects.all(),
            fields=['ingredient', 'recipe'])]


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для рецептов.
    """
    author = ListUserSerializer(read_only=True)
    ingredients = ReadIngredientsRecipeSerializer(
        many=True,
        read_only=True,
        source='amount_ingredient',
    )
    tags = TagSerializer(many=True)
    is_in_shopping_cart = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    image = Base64ImageField(use_url=True, )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return ShoppingCart.objects.filter(
            user=user, recipe=obj
        ).exists() if user.is_authenticated else False

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return Favorite.objects.filter(
            user=user, recipe=obj
        ).exists() if all(
            [user.is_authenticated, self.context.get('request') is not None]
        ) else False


class RecipeCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания рецептов.
    """
    ingredients = IngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(use_url=True, )
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image', 'name', 'text',
            'cooking_time', 'author',
        )

    def validate_cooking_time(self, cooking_time):
        """
        Валидация времени приготовления по рецепту.
        Значение не может быть меньше 1-ой минуты.
        """
        if cooking_time <= 0:
            raise serializers.ValidationError(COCKING_TIME_MESSAGE)
        return cooking_time

    def check_ingredients(self, data):
        validated_items = []
        existed = []
        for item in data:
            ingredient = Ingredient.objects.get(pk=item['id']).name
            if ingredient in validated_items:
                existed.append(ingredient)
            validated_items.append(ingredient)
        if existed:
            raise serializers.ValidationError(
                ERROR_UNIQUE_INGREDIENT.format(value=', '.join(existed))
            )

    def validate(self, data):
        ingredients = data.get('ingredients')
        self.check_ingredients(ingredients)
        data['ingredients'] = ingredients
        return data

    @staticmethod
    def create_ingredients(ingredients, recipe):
        ingredient_list = []
        for ingredient in ingredients:
            amount = ingredient['amount']
            recipe_ingredient = AmountIngredient(
                ingredients=get_object_or_404(
                    Ingredient, id=ingredient['id']
                ),
                recipe=recipe,
                amount=amount
            )
            ingredient_list.append(recipe_ingredient)
        AmountIngredient.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        """
        Создание рецепта.
        """
        pprint(validated_data)
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        image = validated_data.pop('image')
        recipe = Recipe.objects.create(image=image, **validated_data)
        self.create_ingredients(ingredients_data, recipe)
        recipe.tags.set(tags_data)
        return recipe

    def update(self, recipe, validated_data):
        """
        Редактирование рецепта.
        """
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        AmountIngredient.objects.filter(recipe=recipe).delete()
        self.create_ingredients(ingredients, recipe)
        recipe.tags.set(tags)
        return super().update(recipe, validated_data)

    def to_representation(self, recipe):
        return RecipeSerializer(
            recipe,
            context={'request': self.context.get('request')}
        ).data


class RecipeForFollowersSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения рецептов в подписке.
    """
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class FollowSerializer(serializers.ModelSerializer):
    """
    Сериализатор для подписок.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField(read_only=True)
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.author)
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        serializer = RecipeForFollowersSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, author=obj.author).exists()
