from django.db import models

class Category(models.Model):
    title = models.CharField(max_length=150, verbose_name='Назва', unique=True)

    def __str__(self):
        return self.title

class Author(models.Model):
    first_last_name = models.CharField(max_length=200, verbose_name="Ім'я та прізвище")
    birthday = models.DateTimeField(verbose_name='Дата народження')
    ganre_books = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Жанри книг')

    class Meta:
        verbose_name = 'Автор'
        verbose_name_plural = 'Автори'
        ordering = ['first_last_name',]

    def __str__(self):
        return self.first_last_name
    
class Book(models.Model):
    title = models.CharField(max_length=150, verbose_name='Назва')
    slug = models.SlugField(verbose_name='URL', unique=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, verbose_name='Автор', related_name='books')
    category = models.ManyToManyField(Category, verbose_name='Жанр', related_name='books')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата додавання книги')
    updated = models.DateTimeField(auto_now=True, verbose_name='Дата змінення')

    class Meta:
        verbose_name = 'Книга'
        verbose_name_plural = 'Книги'
        ordering = ['title']

    def __str__(self):
        return self.title
    
