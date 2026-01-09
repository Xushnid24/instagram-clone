from django.shortcuts import render, redirect, get_object_or_404
from .models import Post, Comment
from .forms import PostForm, CommentForm

def post_list(request):
    posts = Post.objects.all().order_by('-created_at')

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            post_id = request.POST.get('post_id')
            post = get_object_or_404(Post, id=post_id)
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.save()
            return redirect('post_list')
    else:
        comment_form = CommentForm()

    return render(request, 'posts/post_list.html', {'posts': posts, 'comment_form': comment_form})


def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user   # 🔥 ВАЖНО
            post.save()
            return redirect('post_list')
    else:
        form = PostForm()
    return render(request, 'posts/post_create.html', {'form': form})


def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)  # ← ОБЯЗАТЕЛЬНО!
        if form.is_valid():
            form.save()
            return redirect('post_list')
    else:
        form = PostForm(instance=post)

    return render(request, 'posts/post_edit.html', {'form': form, 'post': post})


def post_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.likes += 1
    post.save()
    return redirect('post_list')


def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('post_list')
    return render(request, 'posts/post_delete.html', {'post': post})

from django.shortcuts import render, get_object_or_404
from .models import Post

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'posts/post_detail.html', {'post': post})

