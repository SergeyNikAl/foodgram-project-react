from django.shortcuts import get_object_or_404
from drf_base64.fields import Base64ImageField
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from recipes.models import (
    AMOUNT_OF_INGREDIENTS,
    COCKING_TIME_MESSAGE,
    RecipeIngredients,
    Ingredient,
    Recipe,
    Tag,
)
from users.models import Follow, User

ERROR_DATA_VALIDATE = (
    'Не удается войти в систему с указанными учетными данными.'
)
EMPTY_EMAIL_OR_PASSWORD = 'Необходимо заполнить поля "email" и "password".'
ERROR_UNIQUE_INGREDIENT = 'Ингредиент {value} уже добавлен.'
ERROR_TAGS_FOR_INGREDIENT = 'Необходимо заполнить хотя бы один тэг для рецепта'
NON_EXISTENT_TAG = 'Тэг {value} не найден.'


class CreateUserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'password', 'username', 'first_name', 'last_name',
        )


class ListUserSerializer(UserSerializer):
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
        if not user.is_authenticated:
            return False
        return Follow.objects.filter(
            user=user, author=obj
        ).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientsSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredients
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount",
        )


class RecipeIngredientsAddSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredients
        fields = (
            "id",
            "amount",
        )


class RecipesListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = UserSerializer(
        read_only=True, default=serializers.CurrentUserDefault()
    )
    ingredients = RecipeIngredientsSerializer(
        many=True, required=True, source="recipe"
    )
    is_favorite = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorite",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )


class RecipesCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientsAddSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()
    name = serializers.CharField()
    cooking_time = serializers.IntegerField()
    author = ListUserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
            'author'
        )

    def validate(self, attrs):
        ingredients = attrs['ingredients']
        ingredients_data = []
        for items in ingredients:
            ingredient = get_object_or_404(Ingredient, id=items['id'])
            if ingredient in ingredients_data:
                raise serializers.ValidationError(
                    ERROR_UNIQUE_INGREDIENT.format(value=ingredient)
                )
            ingredients_data.append(ingredient)
        tags = attrs['tags']
        if not tags:
            raise serializers.ValidationError(ERROR_TAGS_FOR_INGREDIENT)
        for tag in tags:
            if not Tag.objects.filter(name=tag).exists():
                raise serializers.ValidationError(
                    NON_EXISTENT_TAG.format(value=tag)
                )
        return attrs

    def create_ingredients(self, ingredients, recipe):
        RecipeIngredients.objects.bulk_create([
            RecipeIngredients(
                ingredient=ingredient['id'],
                recipe=recipe,
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ])

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) < 1:
            raise serializers.ValidationError(COCKING_TIME_MESSAGE)
        return cooking_time

    def create(self, validated_data):
        author = self.context.get('request').user
        ingredients = validated_data.pop('ingredients')
        if not ingredients:
            raise serializers.ValidationError(AMOUNT_OF_INGREDIENTS)
        for ingredient in ingredients:
            if int(ingredient.get('amount')) < 1:
                raise serializers.ValidationError(ERROR_TAGS_FOR_INGREDIENT)
        image = validated_data.pop('image')
        recipe = Recipe.objects.create(
            image=image, author=author, **validated_data
        )
        recipe.tags.set(validated_data.pop('tags'))
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, obj, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            obj.ingredients.clear()
            self.create_ingredients(ingredients, obj)
        if 'tags' in validated_data:
            tags = validated_data.pop("tags")
            obj.tags.set(tags)
        return super().update(obj, validated_data)

    def to_representation(self, instance):
        return RecipesListSerializer(instance).data


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "image",
            "cooking_time",
        )


class FollowSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source="author.email")
    id = serializers.ReadOnlyField(source="author.id")
    username = serializers.ReadOnlyField(source="author.username")
    first_name = serializers.ReadOnlyField(source="author.first_name")
    last_name = serializers.ReadOnlyField(source="author.last_name")
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, author=obj.author).exists()

    def get_recipes(self, obj):
        queryset = Recipe.objects.filter(author=obj.author)
        return FavoriteRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()
