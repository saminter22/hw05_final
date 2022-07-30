import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.auth import get_user_model
from posts.forms import PostForm
from posts.models import Post, Group, Comment
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Создаем форму, если нужна проверка атрибутов
        cls.form = PostForm()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            id=1,
            group=cls.group,
        )
        cls.comment1 = Comment.objects.create(
            text='Тестовый комментарий1',
            post=cls.post,
            author=cls.user2,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Модуль shutil - библиотека Python с удобными инструментами
        # для управления файлами и директориями:
        # создание, удаление, копирование, перемещение, изменение папок
        # и файлов
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        # self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        self.authorized_client2 = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostFormTests.user)
        self.authorized_client2.force_login(PostFormTests.user2)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'Тестовый текст',
            'group': PostFormTests.group.id,
            'image': uploaded,
        }
        # Отправляем POST-запрос
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем, что создалась запись с заданным слагом
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст',
                group=1,
                image='posts/small.gif'
            ).exists()
        )

    def test_try_guest_create_post(self):
        """У гостя не получается создать запись в Post."""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Гостевой текст',
            'group': PostFormTests.group.id,
        }
        # Отправляем POST-запрос
        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        # Проверяем, не увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count)
        # Проверяем, что запись с заданным текстом не создалась
        self.assertFalse(
            Post.objects.filter(
                text='Гостевой текст',
                group=1,
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        post_id = PostFormTests.post.id
        form_data = {
            'text': 'Тестовый текст2',
            'group': '1',
        }

        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post_id}),
            data=form_data,
            follow=True
        )

        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст2',
            ).exists()
        )

