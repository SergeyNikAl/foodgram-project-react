from django.core.validators import MinValueValidator
from django.db import models

from foodgram.settings import TEXT_SCOPE
from users.models import User

INGREDIENT_NAME_LENGTH = 200
INGREDIENT_MEASUREMENT_UNIT_LENGTH = 200
TAG_NAME_LENGTH = 200
TAG_COLOR_LENGTH = 7
TAG_SLUG_LENGTH = 200
RECIPE_NAME_LENGTH = 200
COCKING_TIME_MESSAGE = 'Время приготовления не может быть менее 1 минуты'
AMOUNT_OF_INGREDIENTS = ('Минимальное колличество ингредиентов не может быть'
                         ' меньше 1')


class Tag(models.Model):
    name = models.CharField(
        'Имя тега',
        max_length=TAG_NAME_LENGTH,
        unique=True,
    )
    color = models.CharField(
        'Цвет',
        max_length=TAG_COLOR_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        'Идентификатор',
        max_length=TAG_SLUG_LENGTH,
        unique=True,
    )

    class Meta:
        ordering = ['id', ]
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name[:TEXT_SCOPE]


class Ingredient(models.Model):
    name = models.CharField(
        'Ингредиент',
        max_length=INGREDIENT_NAME_LENGTH,
        blank=False,
    )
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=INGREDIENT_MEASUREMENT_UNIT_LENGTH,
        blank=False,
    )

    class Meta:
        ordering = ['id', ]
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        'Наименование рецепта',
        max_length=RECIPE_NAME_LENGTH,
    )
    image = models.ImageField(
        'Изображение рецепта',
        upload_to='recipe/',
    )
    text = models.TextField(
        'Описание рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Список ингредиентов',
        through='AmountIngredient',
        related_name='recipes',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
        related_name='recipes',
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (в минутах)',
        validators=[
            MinValueValidator(
                1, message=COCKING_TIME_MESSAGE
            ),
        ]
    )
    pub_date = models.DateTimeField(
        'Дата публикации рецепта',
        auto_now_add=True,
    )

    class Meta:
        ordering = ['-pub_date', ]
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name[:TEXT_SCOPE]


class AmountIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='amount_ingredient',
    )
    ingredients = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        related_name='amount_ingredient',
    )
    amount = models.PositiveSmallIntegerField(
        'Колличество ингредиентов',
        validators=[
            MinValueValidator(
                1, message=AMOUNT_OF_INGREDIENTS
            ),
        ]
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Количество ингридиентов'
        constraints = [
            models.UniqueConstraint(
                fields=('ingredients', 'recipe',),
                name='recipe_ingredient_constraint'
            )
        ]


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='favorite',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Избранный рецепт',
        on_delete=models.CASCADE,
        related_name='favorite',
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='unique_favorite_user_recipe',
            ),
        ]

    def __str__(self):
        return f'{self.recipe} добавлен в избранные пользователем {self.user}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='shopping_cart',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='shopping_cart',
    )

    class Meta:
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='unique_shoppinglist_recipe_user',
            ),
        ]
