from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from .models import Post, Group, Follow
from .forms import PostForm, CommentForm
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
# from django.shortcuts import get_list_or_404
from django.views.decorators.cache import cache_page


User = get_user_model()


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    # posts = Post.objects.select_related('author').all()
    post_list = author.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if request.user.is_authenticated:
        if Follow.objects.filter(user=request.user, author=author):
            context = {
                'page_obj': page_obj,
                'author': author,
                'following': True,
            }
        else:
            context = {
                'page_obj': page_obj,
                'author': author,
                'following': False,
            }
    else:
        context = {
            'page_obj': page_obj,
            'author': author,
            'following': False,
        }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = Post.objects.get(id=post_id)
    # comments = Comment.objects.filter(post=post)
    comments = post.comments.select_related('author').all()
    # comments = get_object_or_404(Comment, post=post)
    # comments = get_list_or_404(Comment, post=post)
    form = CommentForm()
    context = {'post': post,
               'comments': comments,
               'form': form,
               }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(
            request.POST,
            files=request.FILES or None,
        )

        if form.is_valid():
            form = form.save(commit=False)
            form.author = request.user
            form.save()
            return redirect('posts:profile', request.user.username)

        return render(request, 'posts/create_post.html', {'form': form})

    form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post.id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)

    if form.is_valid():
        form.author = request.user
        form = form.save(commit=False)
        form.save()
        return redirect('posts:post_detail', post_id=post.id)

    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    # if request.user != post.author:
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, }
    return render(request, 'posts/follow.html', context)


# @login_required
# def profile_follow(request, username):
#     # Подписаться на автора
#     author = get_object_or_404(User, username=username)
#     if author not in Follow.objects.filter(user=request.user, author=author):
#         if author != request.user:
#             Follow.objects.create(author=author, user=request.user)
#     return redirect('posts:profile', author)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user == author:
        return redirect('posts:profile', username=username)
    if not Follow.objects.filter(user=request.user, author=author):
        Follow.objects.create(author=author, user=request.user)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(user=request.user, author=author):
        fordel = Follow.objects.get(author=author, user=request.user)
        fordel.delete()
    return redirect('posts:profile', author)
