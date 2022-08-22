from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import User
from foodgram.settings import TEXT_SCOPE

INGREDIENT_NAME_LENGTH = 200
INGREDIENT_MEASUREMENT_UNIT_LENGTH = 200
TAG_NAME_LENGTH = 200
TAG_COLOR_LENGTH = 7
TAG_SLUG_LENGTH = 200
RECIPE_NAME_LENGTH = 200
COCKING_TIME_MESSAGE = 'Время приготовления не может быть менее 1 минуты'
AMOUNT_OF_INGREDIENTS = ('Минимальное колличество ингредиентов не может быть'
                         ' меньше 1')


class Ingredient(models.Model):
    name = models.CharField(
        'Ингрдиент',
        max_length=INGREDIENT_NAME_LENGTH,
    )
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=INGREDIENT_MEASUREMENT_UNIT_LENGTH,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'


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

    def __str__(self):
        return self.name[:TEXT_SCOPE]

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipe',
        verbose_name='Автор',
    )
    name = models.CharField(
        'Наименование рецепта',
        max_length=RECIPE_NAME_LENGTH,
    )
    image = models.ImageField(
        'Изображение рецепта',
        upload_to='static/recipe/',
        blank=True,
        null=True,
    )
    text = models.TextField(
        'Описание рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredients',
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

    def __str__(self):
        return self.name[:TEXT_SCOPE]

    class Meta:
        ordering = ['-pub_date', ]
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'


class RecipeIngredients(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient',
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
        verbose_name = 'Количество ингридиента'
        verbose_name_plural = 'Количество ингридиентов'
        constraints = [
            models.UniqueConstraint(
                fields=('ingredient', 'recipe',),
                name='recipe_ingredient_constraint'
            )
        ]


class Favorites(models.Model):
    user = models.OneToOneField(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        null=True,
        related_name='favorites',
    )
    recipe = models.ManyToManyField(
        Recipe,
        verbose_name='Избранный рецепт',
        related_name='favorites',
    )

    @receiver(post_save, sender=User)
    def create_favorite_recipe(sender, instance, created, **kwargs):
        if created:
            return RecipeIngredients.objects.create(user=instance)

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(models.Model):
    user = models.OneToOneField(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        null=True,
    )
    recipe = models.ManyToManyField(
        Recipe,
        verbose_name='Рецепт',
        related_name='shopping_cart',
    )

    @receiver(post_save, sender=User)
    def create_shopping_cart(sender, instance, created, **kwargs):
        if created:
            return ShoppingCart.objects.create(user=instance)

    class Meta:
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'
