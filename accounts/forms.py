from django import forms
from members.models import Member

class ClaimForm(forms.Form):
    buyer = forms.ModelChoiceField(queryset=Member.objects.all())
