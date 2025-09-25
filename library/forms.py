from django import forms
from .models import * 

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'year']
        labels = {
            'title' : 'Назва книги',
            'author' : 'Автор'
        }
        help_texts = {
            'title' : 'Введіть назву книги',
            'author' : 'введіть автора книги'
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')

        if title and len(title) < 3:
            raise forms.ValidationError('К-ть символів має бути не менше 3')
        return title