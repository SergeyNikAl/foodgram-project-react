from django.db import models

from rest_framework.serializers import (ModelSerializer as DRFModelSerializer,
                                        HyperlinkedModelSerializer as DRFHyperlinkedModelSerializer)

from .fields import Base64FileField, Base64ImageField


class Base64ModelSerializerMixin(object):

    def __init__(self, *args, **kwargs):
        self.serializer_field_mapping.update({
            models.FileField: Base64FileField,
            models.ImageField: Base64ImageField,
        })
        super(Base64ModelSerializerMixin, self).__init__(*args, **kwargs)


class ModelSerializer(Base64ModelSerializerMixin, DRFModelSerializer):
    pass


class HyperlinkedModelSerializer(Base64ModelSerializerMixin, DRFHyperlinkedModelSerializer):
    pass
