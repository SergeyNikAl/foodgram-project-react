# Продуктовый помощник Foodgram.

![foodgram_workflow](https://github.com/SergeyNikAl/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg)


### Описание
Сервис, на котором пользователи будут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Сервис «Список покупок» позволит пользователям создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

### Стек технологий:
- Python
- Django
- Django Rest Framework
  (Дописать для удаленного сервера)
---

# Порядок запуска
## Запуск проекта локально
Клонировать репозиторий и перейти в него:
```
git clone https://github.com/SergeyNikAl/foodgram-project-react.git
```

Создать и активировать виртуальное окружение, обновить pip и установить зависимости:
```
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

## Для запуска локально:
```
cd backend
python manage.py runserver
```

Создать базу данных:
```
cd backend
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

Загрузить предуставновленнуые данные по рецептам и тэгам:
```
python manage.py csv_manager
python manage.py tags_manager
```

Заупстить сервер:
```
python manage.py runserver
```

Для запуска frontend(через bash):
- запустить bash
- найти директорию проекта foodgram-project-react
- пройти в директорию infra
```
cd infra
docker-compose up --build
```

Сервис будет доступен по адресу localhost/signup



