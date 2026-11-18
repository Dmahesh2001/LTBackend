import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status

from apps.core.testing import APITestCase
from apps.users.models import User

from .models import Comment, Like, Post, SavedPost

MEDIA_ROOT = tempfile.mkdtemp()


def make_image(name='photo.png', fmt='PNG'):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), 'orange').save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{fmt.lower()}')


class FeedTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.alice = User.objects.create_user(email='alice@example.com', password='x', first_name='Alice')
        self.bob = User.objects.create_user(email='bob@example.com', password='x', first_name='Bob')
        self.client.force_authenticate(self.alice)

    def post_url(self, post, suffix=''):
        return reverse(f'post-{suffix or "detail"}', args=[post.pk])


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostTests(FeedTestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_feed_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse('post-list')).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_post_with_image(self):
        response = self.client.post(
            reverse('post-list'), {'caption': 'Walk time', 'image': make_image()}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['caption'], 'Walk time')
        self.assertTrue(response.data['image'].startswith('http://testserver/media/posts/'))
        self.assertEqual(response.data['author']['first_name'], 'Alice')
        self.assertNotIn('email', response.data['author'])
        self.assertEqual(response.data['like_count'], 0)
        self.assertFalse(response.data['is_liked'])

    def test_create_text_only_post(self):
        response = self.client.post(reverse('post-list'), {'caption': 'Hello'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['image'])

    def test_empty_post_is_rejected(self):
        response = self.client.post(reverse('post-list'), {'caption': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_image_upload_is_rejected(self):
        fake = SimpleUploadedFile('photo.png', b'not an image', content_type='image/png')
        response = self.client.post(reverse('post-list'), {'image': fake}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)

    def test_feed_is_newest_first_with_counts_and_viewer_state(self):
        older = Post.objects.create(author=self.bob, caption='older')
        newer = Post.objects.create(author=self.bob, caption='newer')
        Like.objects.create(user=self.alice, post=older)
        Like.objects.create(user=self.bob, post=older)
        Comment.objects.create(post=older, author=self.bob, text='hi')
        SavedPost.objects.create(user=self.alice, post=older)

        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual([p['id'] for p in results], [newer.pk, older.pk])
        self.assertEqual(results[1]['like_count'], 2)
        self.assertEqual(results[1]['comment_count'], 1)
        self.assertTrue(results[1]['is_liked'])
        self.assertTrue(results[1]['is_saved'])
        self.assertEqual(results[0]['like_count'], 0)
        self.assertFalse(results[0]['is_liked'])

    def test_feed_cursor_pagination(self):
        for i in range(5):
            Post.objects.create(author=self.bob, caption=str(i))
        first = self.client.get(reverse('post-list'), {'page_size': 3})
        self.assertEqual(len(first.data['results']), 3)
        second = self.client.get(first.data['next'])
        self.assertEqual(len(second.data['results']), 2)
        self.assertIsNone(second.data['next'])

    def test_filter_feed_by_author(self):
        Post.objects.create(author=self.alice, caption='mine')
        Post.objects.create(author=self.bob, caption='bob')
        response = self.client.get(reverse('post-list'), {'author': self.bob.pk})
        self.assertEqual([p['caption'] for p in response.data['results']], ['bob'])
        self.assertEqual(self.client.get(reverse('post-list'), {'author': 'x'}).status_code, 400)

    def test_author_can_edit_caption_but_others_cannot(self):
        post = Post.objects.create(author=self.alice, caption='old')
        response = self.client.patch(self.post_url(post), {'caption': 'new'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['caption'], 'new')

        self.client.force_authenticate(self.bob)
        response = self.client.patch(self.post_url(post), {'caption': 'hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_author_or_staff_can_delete(self):
        post = Post.objects.create(author=self.alice, caption='x')
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.delete(self.post_url(post)).status_code, status.HTTP_403_FORBIDDEN)

        self.bob.is_staff = True
        self.bob.save()
        self.assertEqual(self.client.delete(self.post_url(post)).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.exists())


class LikeTests(FeedTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(author=self.bob, caption='Good dog')

    def test_like_and_unlike_are_idempotent(self):
        url = self.post_url(self.post, 'like')
        for _ in range(2):
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {'liked': True, 'like_count': 1})
        for _ in range(2):
            response = self.client.delete(url)
            self.assertEqual(response.data, {'liked': False, 'like_count': 0})

    def test_like_missing_post_returns_404(self):
        response = self.client.post(reverse('post-like', args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_who_liked(self):
        Like.objects.create(user=self.bob, post=self.post)
        response = self.client.get(self.post_url(self.post, 'likes'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['user']['first_name'], 'Bob')


class SaveTests(FeedTestCase):
    def test_save_unsave_and_list_saved(self):
        first = Post.objects.create(author=self.bob, caption='first')
        second = Post.objects.create(author=self.bob, caption='second')
        Post.objects.create(author=self.bob, caption='not saved')

        self.assertEqual(self.client.post(self.post_url(second, 'save')).data, {'saved': True})
        self.assertEqual(self.client.post(self.post_url(first, 'save')).data, {'saved': True})

        response = self.client.get(reverse('post-saved'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Most recently saved first, regardless of when the post was created.
        self.assertEqual([p['id'] for p in response.data['results']], [first.pk, second.pk])
        self.assertTrue(all(p['is_saved'] for p in response.data['results']))
        self.assertIn('saved_at', response.data['results'][0])

        self.assertEqual(self.client.delete(self.post_url(first, 'save')).data, {'saved': False})
        response = self.client.get(reverse('post-saved'))
        self.assertEqual([p['id'] for p in response.data['results']], [second.pk])

    def test_saved_list_is_private(self):
        post = Post.objects.create(author=self.bob, caption='x')
        SavedPost.objects.create(user=self.bob, post=post)
        self.assertEqual(self.client.get(reverse('post-saved')).data['results'], [])


class CommentTests(FeedTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(author=self.bob, caption='Good dog')
        self.comments_url = reverse('post-comments', args=[self.post.pk])

    def test_add_and_list_comments_oldest_first(self):
        response = self.client.post(self.comments_url, {'text': '  So cute!  '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['text'], 'So cute!')
        self.assertEqual(response.data['post'], self.post.pk)
        self.assertEqual(response.data['author']['id'], self.alice.pk)

        self.client.force_authenticate(self.bob)
        self.client.post(self.comments_url, {'text': 'Thanks'}, format='json')

        response = self.client.get(self.comments_url)
        self.assertEqual([c['text'] for c in response.data['results']], ['So cute!', 'Thanks'])
        self.assertEqual(self.client.get(self.post_url(self.post)).data['comment_count'], 2)

    def test_blank_comment_is_rejected(self):
        response = self.client.post(self.comments_url, {'text': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comment_on_missing_post_returns_404(self):
        response = self.client.post(reverse('post-comments', args=[999999]), {'text': 'hi'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_comment_author_can_edit(self):
        comment = Comment.objects.create(post=self.post, author=self.alice, text='typo')
        url = reverse('comment-detail', args=[comment.pk])
        response = self.client.patch(url, {'text': 'fixed'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'fixed')

        # The post's author can't rewrite other people's comments.
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.patch(url, {'text': 'x'}, format='json').status_code, 403)

    def test_comment_delete_permissions(self):
        carol = User.objects.create_user(email='carol@example.com', password='x')
        own = Comment.objects.create(post=self.post, author=self.alice, text='mine')
        other = Comment.objects.create(post=self.post, author=self.alice, text='on bob post')

        # A stranger can't delete it.
        self.client.force_authenticate(carol)
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[own.pk])).status_code, 403)

        # The comment's author can.
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[own.pk])).status_code, 204)

        # The post's author can remove comments on their own post.
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[other.pk])).status_code, 204)
        self.assertFalse(Comment.objects.exists())

    def test_deleting_post_deletes_its_comments_likes_and_saves(self):
        Comment.objects.create(post=self.post, author=self.alice, text='x')
        Like.objects.create(post=self.post, user=self.alice)
        SavedPost.objects.create(post=self.post, user=self.alice)
        self.client.force_authenticate(self.bob)
        self.client.delete(self.post_url(self.post))
        self.assertFalse(Comment.objects.exists() or Like.objects.exists() or SavedPost.objects.exists())
