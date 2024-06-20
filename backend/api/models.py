from django.db import models
from django.dispatch import receiver
from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models.signals import post_save


class Message(models.Model):
    subject = models.CharField(max_length=200)
    body = models.TextField()


class Profile(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    is_test = models.BooleanField(default=False)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('pk', 'user', 'is_test')


class Image(models.Model):

    img_id              = models.CharField(max_length=100, unique=True)
    extension           = models.CharField(max_length=15, blank=True, default="")
    img_path            = models.CharField(max_length=200)
    ground_truth        = models.TextField(blank=True, null=True)


class Annotation(models.Model):
    annotator = models.ForeignKey('auth.User', to_field="id", related_name='annotations', on_delete=models.PROTECT)
    image = models.ForeignKey(Image, to_field="img_id", related_name='annotations', on_delete=models.PROTECT)
    annotation = models.TextField(blank=True)
    text = models.TextField(blank=True)
    real_button = models.BooleanField(default=False)
    fake_button = models.BooleanField(default=False)
    ground_truth = models.TextField(blank=True, null=True)
    annotation_svg = models.TextField(blank=True, null=True)
    annotation_times = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = [["annotator", "image"]]
    
    def save(self, *args, **kwargs):
        # Fetch ground truth from the associated Image and set it in the Annotation
        if not self.ground_truth and self.image:
            self.ground_truth = self.image.ground_truth
        super().save(*args, **kwargs)


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Message
        fields = ('pk', 'url', 'subject', 'body')


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Image
        fields = (
            'pk', 'img_id', 'extension', 'img_path',
        )


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ('pk', 'annotator', 'image', 'annotation')


class UserSerializer(serializers.ModelSerializer):
    annotations = serializers.PrimaryKeyRelatedField(many=True, queryset=Annotation.objects.all())

    class Meta:
        model = User
        fields = ['id', 'username', 'annotations']
