# coding: utf-8
from django.db import models


class Category(models.Model):
    category_name_ru = models.CharField(max_length=250)
    category_name_en = models.CharField(max_length=250)

    def __str__(self):
        return self.category_name_en


class Question(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    question_text_ru = models.CharField(max_length=250)
    question_text_en = models.CharField(max_length=250)
    answer_url = models.URLField(blank=True)
    answer_text_ru = models.CharField(max_length=250)
    answer_text_en = models.CharField(max_length=250)

    def __str__(self):
        return self.question_text_en


class WhitePhone(models.Model):
    phone_number_text = models.CharField(max_length=15, primary_key=True)

    def __str__(self):
        return self.phone_number_text

class ViberUser(models.Model):
    user_id = models.CharField(max_length=50, primary_key=True)
    phone = models.ForeignKey(WhitePhone, on_delete=models.CASCADE)
    user_language = models.CharField(max_length=2, null=True)

    def __str__(self):
        return '%s %s' % (self.user_id, self.phone)


class Message(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    description = models.CharField(max_length=100)
    text_ru = models.TextField()
    text_en = models.TextField()

    def __str__(self):
        return self.description
