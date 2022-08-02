# posts/tests/test_urls.py
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
# from django.test import  override_settings
from http import HTTPStatus

from posts.models import Post, Group
from django.core.cache import cache

User = get_user_model()


class PostURLTests(TestCase):
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
        # Создадим запись в БД для проверки доступности адреса post/1/
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            pk=1,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        self.authorized_client2 = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostURLTests.user)
        self.authorized_client2.force_login(PostURLTests.user2)
        cache.clear()

    def test_pages_exists_at_desired_location(self):
        """Страницы сайта доступны для гостей или отсутствуют
        и дают верный ответ сервера."""
        pair_address_expect_equal = {
            '/': HTTPStatus.OK,
            f'/posts/{PostURLTests.post.pk}/': 200,
            f'/profile/{PostURLTests.post.author}/': 200,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, expect in pair_address_expect_equal.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, expect)

    def test_post_id_edit_guest_url_exists_at_desired_location(self):
        """Страница /post/<int:post_id>/edit переадресует гостя на
        авторизацию."""
        response = self.guest_client.get(
            f'/posts/{PostURLTests.post.pk}/edit/', follow=True)
        self.assertRedirects(
            response,
            (f'/auth/login/?next=/posts/{PostURLTests.post.pk}/edit/'))

    def test_post_create_url_redirects_guest_for_autorization(self):
        """Страница /create/ переадресует гостя на авторизацию."""
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна только авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_id_edit_url_exists_at_desired_location(self):
        """Страница /post/<int:post_id>/edit переадресует не автора."""
        response = self.authorized_client2.get(
            f'/posts/{PostURLTests.post.pk}/edit/', follow=True)
        self.assertRedirects(response, f'/posts/{PostURLTests.post.pk}/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Адреса и их шаблоны
        url_templates_names = {
            '/': 'posts/index.html',
            '/group/group-slug/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/unexisting': 'core/404.html'
        }
        for address, template in url_templates_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_comment_denied_to_guest(self):
        """Создание комментария не доступно гостю."""
        response = self.guest_client.get(
            f'/posts/{PostURLTests.post.pk}/comment/', follow=True)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{PostURLTests.post.pk}/comment/')

    def test_subscribe_for_authorized_user_redirect_to_authorization(self):
        """Подписка доступна только для авторизованного пользователя."""
        response = self.guest_client.get(
            f'/profile/{PostURLTests.user}/follow/', follow=True)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/profile/{PostURLTests.user}/follow/')

    def test_comments_create_url_exists_at_desired_location_for_auth(self):
        """Создание комментария доступно только авторизованному."""
        response = self.authorized_client.get(
            f'/posts/{PostURLTests.post.pk}/comment/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_subscribe_authors_url_exists_at_desired_location_for_auth(self):
        """Смотреть посты избранных автором можно только авторизованному."""
        response = self.authorized_client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_subscribe_url_exists_at_desired_location_for_authorization(self):
        """Подписка доступна только авторизованному пользователю."""
        response = self.authorized_client.get(
            f'/profile/{PostURLTests.user}/follow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unsubscribe_url_exists_at_desired_location_for_auth(self):
        """Отписка доступна только авторизованному пользователю."""
        response = self.authorized_client.get(
            f'/profile/{PostURLTests.user}/unfollow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
