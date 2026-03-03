from django import forms
from .models import Participant, Match, Tournament
from datetime import date


class TournamentForm(forms.ModelForm):
    """Форма создания турнира"""

    class Meta:
        model = Tournament
        fields = ['name', 'date', 'location', 'registration_deadline', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название турнира'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Место проведения'}),
            'registration_deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Название турнира',
            'date': 'Дата проведения',
            'location': 'Место проведения',
            'registration_deadline': 'Дедлайн регистрации',
            'is_active': 'Активный турнир',
        }
        help_texts = {
            'registration_deadline': 'Дата, до которой принимаются заявки',
        }


class ParticipantForm(forms.ModelForm):
    """Форма регистрации участника"""

    class Meta:
        model = Participant
        fields = ['last_name', 'first_name', 'birth_date', 'gender', 'weight', 'club', 'coach']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иван'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '65.5'}),
            'club': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Клуб "Восток"'}),
            'coach': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Петров А.И.'}),
        }

    def clean_birth_date(self):
        birth_date = self.cleaned_data['birth_date']
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        if age < 6:
            raise forms.ValidationError('Минимальный возраст участника - 6 лет')
        if age > 60:
            raise forms.ValidationError('Проверьте дату рождения')

        return birth_date


class MatchResultForm(forms.ModelForm):
    """Форма ввода результатов поединка"""

    class Meta:
        model = Match
        fields = ['score_p1', 'score_p2', 'winner', 'status']
        widgets = {
            'score_p1': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'score_p2': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'winner': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Ограничиваем выбор победителя только участниками этого боя
            participants = []
            if self.instance.participant1:
                participants.append(self.instance.participant1.id)
            if self.instance.participant2:
                participants.append(self.instance.participant2.id)
            self.fields['winner'].queryset = Participant.objects.filter(id__in=participants)


class ExcelUploadForm(forms.Form):
    """Форма для загрузки Excel файла"""
    excel_file = forms.FileField(
        label='Выберите Excel файл',
        help_text='Файл должен содержать колонки: Фамилия, Имя, Дата рождения, Пол, Вес, Клуб, Тренер',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'})
    )
    clear_existing = forms.BooleanField(
        label='Очистить существующих участников',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )