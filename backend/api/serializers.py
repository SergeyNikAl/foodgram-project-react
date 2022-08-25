from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (
    AMOUNT_OF_INGREDIENTS,
    COCKING_TIME_MESSAGE,
    AmountIngredients,
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag
)
from rest_framework import serializers
from users.models import Follow, User
from users.validators import UsernameValidation

ERROR_TAGS_FOR_INGREDIENT = 'Необходимо заполнить хотя бы один тэг для рецепта'


class CreateUserSerializer(UserCreateSerializer, UsernameValidation):
    """
    Сериализатор для регистрации пользователей.
    """

    class Meta:
        model = User
        fields = (
            'email', 'password', 'username', 'first_name', 'last_name',
        )


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
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиентов.
    """

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления ингредиентов при создании рецепта.
    """
    id = serializers.IntegerField()

    class Meta:
        model = AmountIngredients
        fields = ('id', 'amount')


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
        model = AmountIngredients
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для рецептов.
    """
    author = ListUserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
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
        ).exists() if any(
            [user.is_authenticated, self.context.get('request') is not None]
        ) else False

    @staticmethod
    def get_ingredients(obj):
        return ReadIngredientsRecipeSerializer(
            AmountIngredients.objects.filter(recipe=obj),
            many=True
        ).data


class RecipeCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания рецептов.
    """
    ingredients = IngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(use_url=True, )
    name = serializers.CharField()
    cooking_time = serializers.IntegerField()
    author = ListUserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image', 'name', 'text',
            'cooking_time', 'author',
        )

    @staticmethod
    def create_ingredients(ingredients, recipe):
        for ingredient in ingredients:
            amount = ingredient['amount']
            if AmountIngredients.objects.filter(
                    recipe=recipe,
                    ingredients=get_object_or_404(
                        Ingredient, id=ingredient['id'])
            ).exists():
                amount += F('amount')
            AmountIngredients.objects.update_or_create(
                recipe=recipe,
                ingredients=get_object_or_404(
                    Ingredient, id=ingredient['id']
                ),
                defaults={'amount': amount}
            )

    def create(self, validated_data):
        """
        Создание рецепта.
        """
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
        AmountIngredients.objects.filter(recipe=recipe).delete()
        self.create_ingredients(ingredients, recipe)
        recipe.tags.set(tags)
        return super().update(recipe, validated_data)

    def to_representation(self, recipe):
        return RecipeSerializer(
            recipe,
            context={'request': self.context.get('request')}
        ).data

    def validate_cooking_time(self, cooking_time):
        """
        Валидация времени приготовления по рецепту.
        Значение не может быть меньше 1-ой минуты.
        """
        if cooking_time <= 0:
            raise serializers.ValidationError(COCKING_TIME_MESSAGE)
        return cooking_time

    def validate_ingredients(self, ingredients):
        """
        Валидация колличества ингредиентов в рецепте.
        Необходимо заполнить хотя бы 1 рецепт.
        """
        for ingredient in ingredients:
            if int(ingredient['amount']) <= 0:
                raise serializers.ValidationError(AMOUNT_OF_INGREDIENTS)
        return ingredients


class RecipeForFollowersSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вывода рецептов в избранном и корзине покупок.
    """
    image = Base64ImageField(use_url=True, )

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeFollowUserField(serializers.Field):
    """
    Сериализатор для вывода рецептов в подписках.
    """

    def get_attribute(self, instance):
        return Recipe.objects.filter(author=instance.author)

    def to_representation(self, recipes_list):
        recipes_data = []
        for recipes in recipes_list:
            recipes_data.append(
                {
                    "id": recipes.id,
                    "name": recipes.name,
                    "image": recipes.image.url,
                    "cooking_time": recipes.cooking_time,
                }
            )
        return recipes_data


class FollowSerializer(serializers.ModelSerializer):
    """
    Сериализатор для подписок.
    """
    recipes = RecipeFollowUserField()
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

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, author=obj.author).exists()
