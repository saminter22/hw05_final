# posts/tests/test_views.py
import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
# from django.views.decorators.cache import cache_page
from django.core.cache import cache

from posts.models import Post, Group, Comment

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# @override_settings(CACHES={'default': {
#     'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }})
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='group-slug2',
            description='Тестовое описание2',
        )

        # Создадим запись в БД для проверки доступности адреса post/1/
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            id=1,
            group=cls.group,
        )
        cls.post2 = Post.objects.create(
            author=cls.user2,
            text='Тестовый пост2',
            id=2,
            group=cls.group2,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostPagesTests.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "reverse(name): имя_html_шаблона"
        pages_templates_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args={PostPagesTests.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    args={f'{PostPagesTests.post.author}'}):
            'posts/profile.html',
            reverse('posts:post_detail',
                    args={f'{PostPagesTests.post.id}'}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    args={PostPagesTests.post.id}): 'posts/create_post.html',
        }
        for reverse_name, template, in pages_templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка словаря контекста главной страницы (передается список постов)
    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        # Словарь ожидаемых полей первого элемента списка
        object_index = response.context['page_obj']
        first_object_text = object_index[0].text
        first_object_group = object_index[0].group
        first_object_author = object_index[0].author
        first_object_id = object_index[0].id
        self.assertEqual(first_object_text, PostPagesTests.post2.text)
        self.assertEqual(first_object_group, PostPagesTests.post2.group)
        self.assertEqual(first_object_author, PostPagesTests.post2.author)
        self.assertEqual(first_object_id, PostPagesTests.post2.id)

    # Проверка словаря контекста списка постов по группе
    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': PostPagesTests.group.slug}))
        object_group = response.context['group']
        self.assertEqual(object_group.title, PostPagesTests.group.title)

    # Проверка словаря контекста списка постов по автору
    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': PostPagesTests.post.author}))
        object_author = response.context['author']
        self.assertEqual(object_author.username, PostPagesTests.user.username)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': PostPagesTests.post.id}))
        object_post = response.context['post']
        self.assertEqual(object_post.text, PostPagesTests.post.text)
        self.assertEqual(object_post.group, PostPagesTests.post.group)
        self.assertEqual(object_post.author, PostPagesTests.post.author)
        self.assertEqual(object_post.id, PostPagesTests.post.id)

    def test_create_post_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_correct_context(self):
        """Шаблон edit_post при редактировании поста с заданным id сформирован
        с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': PostPagesTests.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_showing_new_post_in_his_group(self):
        """Пост появляется на странице указанной группы"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'group-slug2'}))
        self.assertEqual(
            response.context['page_obj'][0].group.title,
            PostPagesTests.group2.title
        )
        self.assertNotEqual(
            response.context['page_obj'][0].group.title,
            PostPagesTests.group.title
        )

    def test_showing_new_post_in_his_author(self):
        """Пост появляется на странице указанного автора"""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': PostPagesTests.post.author}))
        self.assertEqual(
            response.context['page_obj'][0].author.username, 'auth')
        self.assertNotEqual(
            response.context['page_obj'][0].author.username, 'auth2')


# @override_settings(CACHES={'default': {
#     'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }})
class PaginatorViewsTest(TestCase):
    # Здесь создаются фикстуры: клиент и 13 тестовых записей.
    @ classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='group-slug1',
            description='Тестовое описание1',
        )
        # for i in range(13):
        #     Post.objects.create(
        #         author=cls.user,
        #         # author='leo',
        #         text=f'Тестовый пост {i}',
        #         id=i,
        #         group=cls.group,
        #     )
        Post.objects.bulk_create(
            [Post(
                id=i,
                author=cls.user,
                text=f'Тестовый пост {i}',
                group=cls.group,
            ) for i in range(13)
            ])

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PaginatorViewsTest.user)
        cache.clear()

    def test_first_page_index_contains_ten_records(self):
        """Проверка постов на странице index: 10 на 1-й, 3 на второй."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_page_group_list_contains_ten_records(self):
        """Проверка постов на странице group_list: 10 на 1-й, 3 на второй."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'group-slug1'}))
        self.assertEqual(len(response.context['page_obj']), 10)
        response = self.client.get(reverse('posts:group_list', kwargs={
            'slug': 'group-slug1'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_page_profile_contains_ten_records(self):
        """Проверка постов на странице profile: 10 на 1-й, 3 на второй."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': 'auth'}))
        self.assertEqual(len(response.context['page_obj']), 10)
        response = self.client.get(reverse('posts:profile', kwargs={
            'username': 'auth'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)


# @override_settings(CACHES={'default': {
#     'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }})
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ImageViewTest(TestCase):
    @ classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='group-slug1',
            description='Тестовое описание1',
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            id=1,
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(ImageViewTest.user)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_detail_context_with_img(self):
        """В шаблон post_detail передается изображение в словаре."""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': ImageViewTest.post.id}))
        object_post = response.context['post']
        self.assertEqual(object_post.text, ImageViewTest.post.text)
        self.assertEqual(object_post.group, ImageViewTest.post.group)
        self.assertEqual(object_post.author, ImageViewTest.post.author)
        self.assertEqual(object_post.id, ImageViewTest.post.id)
        self.assertEqual(object_post.image, ImageViewTest.post.image)

    def test_home_page_context_with_img(self):
        """В Шаблон index передается изображение в словаре."""
        response = self.authorized_client.get(reverse('posts:index'))
        # Словарь ожидаемых полей первого элемента списка
        object_index = response.context['page_obj']
        first_object_text = object_index[0].text
        first_object_group = object_index[0].group
        first_object_author = object_index[0].author
        first_object_id = object_index[0].id
        first_object_image = object_index[0].image
        self.assertEqual(first_object_text, ImageViewTest.post.text)
        self.assertEqual(first_object_group, ImageViewTest.post.group)
        self.assertEqual(first_object_author, ImageViewTest.post.author)
        self.assertEqual(first_object_id, ImageViewTest.post.id)
        self.assertEqual(first_object_image, ImageViewTest.post.image)

    # Проверка словаря контекста списка постов по автору
    def test_profile_page_context_with_img(self):
        """В Шаблон profile передается изображение в словаре."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': ImageViewTest.post.author}))
        # Словарь ожидаемых полей первого элемента списка
        object_index = response.context['page_obj']
        first_object_text = object_index[0].text
        first_object_group = object_index[0].group
        first_object_author = object_index[0].author
        first_object_id = object_index[0].id
        first_object_image = object_index[0].image
        self.assertEqual(first_object_text, ImageViewTest.post.text)
        self.assertEqual(first_object_group, ImageViewTest.post.group)
        self.assertEqual(first_object_author, ImageViewTest.post.author)
        self.assertEqual(first_object_id, ImageViewTest.post.id)
        self.assertEqual(first_object_image, ImageViewTest.post.image)

    # Проверка словаря контекста списка постов по автору
    def test_group_page_context_with_img(self):
        """В Шаблон group_list передается изображение в словаре."""
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': ImageViewTest.group.slug}))
        # Словарь ожидаемых полей первого элемента списка
        object_index = response.context['page_obj']
        first_object_text = object_index[0].text
        first_object_group = object_index[0].group
        first_object_author = object_index[0].author
        first_object_id = object_index[0].id
        first_object_image = object_index[0].image
        self.assertEqual(first_object_text, ImageViewTest.post.text)
        self.assertEqual(first_object_group, ImageViewTest.post.group)
        self.assertEqual(first_object_author, ImageViewTest.post.author)
        self.assertEqual(first_object_id, ImageViewTest.post.id)
        self.assertEqual(first_object_image, ImageViewTest.post.image)


# @override_settings(CACHES={'default': {
#     'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }})
class CacheViewsTest(TestCase):
    @ classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='group-slug1',
            description='Тестовое описание1',
        )
        # Post.objects.bulk_create(
        #     [Post(
        #         id=i,
        #         author=cls.user,
        #         text=f'Тестовый пост {i}',
        #         group=cls.group,
        #     ) for i in range(5)
        #     ])
        Post.objects.create(
            id=1,
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(CacheViewsTest.user)
        cache.clear()

    def test_cache_records_in_index_page(self):
        """Проверка кеширования постов на главной странице."""
        response = self.client.get(reverse('posts:index'))
        object_index1 = response.content
        Post.objects.create(
            id=2,
            author=CacheViewsTest.user,
            text='Тестовый пост2',
            group=CacheViewsTest.group,
        )
        response = self.client.get(reverse('posts:index'))
        object_index2 = response.content
        self.assertEqual(object_index1, object_index2)
        cache.clear()
        # dpost = Post.objects.filter(id=2)
        # dpost.delete()

        # response = self.client.get(reverse('posts:index'))
        # object_index3 = response.content
        # self.assertEqual(object_index1, object_index3)


class PostCommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='group-slug2',
            description='Тестовое описание2',
        )

        # Создадим запись в БД для проверки доступности адреса post/1/
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            id=1,
            group=cls.group,
        )
        cls.post2 = Post.objects.create(
            author=cls.user2,
            text='Тестовый пост2',
            id=2,
            group=cls.group2,
        )

        cls.comment1 = Comment.objects.create(
            text='Тестовый комментарий1',
            post=cls.post,
            author=cls.user2,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostCommentsTests.user)
        cache.clear()

    def test_showing_comments_in_post_page(self):
        """Комментарий появляется на странице поста"""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': PostCommentsTests.post.id}))
        object_comments = response.context['comments']
        first_object_comment = object_comments[0].text
        self.assertEqual(first_object_comment, PostCommentsTests.comment1.text)
