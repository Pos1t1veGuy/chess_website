from django.test import TestCase
from AUTH.models import User
from django.urls import reverse

class LeaderboardTest(TestCase):
    def setUp(self):
        # Создаем несколько пользователей
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password1', first_name='User')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password2', first_name='User', last_name='Two')
        self.user3 = User.objects.create_user(username='user3', email='user3@example.com', password='password3', last_name='Three')

    def test_leaderboard_view(self):
        # Создаем URL для представления списка лидеров
        url = reverse('chess:leaders')
        
        # Отправляем GET-запрос к странице лидеров
        response = self.client.get(url)
        open('index.html', 'wb').write(response.content)

        # Проверяем, что страница возвращает код 200 (ОК)
        self.assertEqual(response.status_code, 200)
