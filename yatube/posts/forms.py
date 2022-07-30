from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        # labels = {
        #     'text': 'Текст поста',
        #     'group': 'Группа'
        # }
        # help_texts = {
        #     'text': 'Введите какой-нибудь гениальный текст',
        #     'group': 'Группу можно не выбирать, ну а все же?'
        # }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
