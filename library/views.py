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
            author, created = Author.objects.get_or_create(first_last_name=author_name)

            # отримуємо об’єкт книги з форми, але не зберігаємо
            book = form.save(commit=False)
            book.author = author
            book.save()

            # якщо є зв’язки many-to-many, їх треба зберегти після save()
            form.save_m2m()

            return redirect('book_list')
    else:
        form = BookForm()
    return render(request, 'library/book_form.html', {'form': form})


def book_update(request, slug):
    book = get_object_or_404(Book, slug = slug)
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            return redirect('book_detail', slug = book.slug)
    else:
        form = BookForm(instance=book)
    return render(request, 'library/book_form.html', {'form':form, 'book':book})

def book_delete(request, slug):
    book = get_object_or_404(Book, slug=slug)
    if request.method == 'POST':
        book.delete()
        return redirect('book_list')
    return render(request, 'library/book_confirm_delete.html', {'book':book})