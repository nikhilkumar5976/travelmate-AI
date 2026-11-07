from django import forms


class ChatForm(forms.Form):
    text = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Write a message...'}),
        label='',
    )