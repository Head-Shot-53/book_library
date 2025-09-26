from django.shortcuts import render, get_object_or_404, redirect
from .models import Book, Author
from .forms import BookForm
from django.utils.text import slugify

def book_list(request):
    query = request.GET.get('q')
    books = Book.objects.all()
    if query:
        books = books.filter(title__icontains = query)
    return render(request, 'library/books_list.html', {'books':books})


def book_detail(request, slug):
    book = get_object_or_404(Book, slug = slug)
    return render(request, 'library/book_detail.html', {'book':book})

def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            author_name = form.cleaned_data['author_name']
            author, created = Author.objects.get_or_create(first_last_name = author_name)

            book = Book(
                title = form.cleaned_data['title'],
                year = form.cleaned_data['year'],
                author = author
            )
            book.save()
            return redirect('book_list')
    else:
        form = BookForm()
    return render(request, 'library/book_form.html', {'form':form})

