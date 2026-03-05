from django.db import models
from django.core.exceptions import ValidationError
from datetime import date


class Tournament(models.Model):
    """Турнир"""
    name = models.CharField(max_length=200, verbose_name="Название турнира")
    date = models.DateField(verbose_name="Дата проведения")
    location = models.CharField(max_length=300, verbose_name="Место проведения",
                                default="г. Альметьевск, пр-кт Строителей, д.9А Спортивный Комплекс «Батыр»")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    registration_deadline = models.DateField(verbose_name="Дедлайн регистрации", null=True, blank=True)

    class Meta:
        verbose_name = "Турнир"
        verbose_name_plural = "Турниры"

    def __str__(self):
        return f"{self.name} - {self.date}"


class Participant(models.Model):
    """Участник турнира"""
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    birth_date = models.DateField(verbose_name="Дата рождения")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Пол")
    weight = models.FloatField(verbose_name="Вес (кг)")
    club = models.CharField(max_length=200, verbose_name="Клуб/Школа")
    coach = models.CharField(max_length=200, blank=True, verbose_name="Тренер")

    # Система автоматически определит категорию
    age_category = models.CharField(max_length=20, blank=True, editable=False, verbose_name="Возрастная категория")
    weight_category = models.CharField(max_length=50, blank=True, editable=False, verbose_name="Весовая категория")

    # Для отслеживания импорта из Excel
    source_file = models.CharField(max_length=255, blank=True, null=True, verbose_name="Файл-источник")
    row_number = models.IntegerField(blank=True, null=True, verbose_name="Номер строки в файле")

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='participants')
    registered_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    def save(self, *args, **kwargs):
        # Автоматически определяем категории при сохранении
        self.age_category = self.determine_age_category()
        self.weight_category = self.determine_weight_category()
        super().save(*args, **kwargs)

    def determine_age_category(self):
        """Определение возрастной категории по правилам"""
        age = self.age()
        if 6 <= age <= 7:
            return "6-7 лет"
        elif 8 <= age <= 9:
            return "8-9 лет"
        elif 10 <= age <= 11:
            return "10-11 лет"
        elif 12 <= age <= 13:
            return "12-13 лет"
        elif 14 <= age <= 15:
            return "14-15 лет"
        elif 16 <= age <= 17:
            return "16-17 лет"
        elif age >= 18:
            return "18 лет и старше"
        return "Не определена"

    def determine_weight_category(self):
        """Определение весовой категории по правилам из положения"""
        age = self.age()
        weight = self.weight

        # 6-7 лет
        if 6 <= age <= 7:
            if self.gender == 'M':  # Мальчики
                if weight <= 20:
                    return "до 20 кг"
                elif weight <= 22.5:
                    return "до 22,5 кг"
                elif weight <= 25:
                    return "до 25 кг"
                elif weight <= 27.5:
                    return "до 27,5 кг"
                elif weight <= 30:
                    return "до 30 кг"
                elif weight <= 35:
                    return "до 35 кг"
                else:
                    return "свыше 35 кг"
            else:  # Девочки
                if weight <= 20:
                    return "до 20 кг"
                elif weight <= 25:
                    return "до 25 кг"
                elif weight <= 30:
                    return "до 30 кг"
                elif weight <= 35:
                    return "до 35 кг"
                else:
                    return "свыше 35 кг"

        # 8-9 лет
        elif 8 <= age <= 9:
            if self.gender == 'M':  # Мальчики
                if weight <= 25:
                    return "до 25 кг"
                elif weight <= 27.5:
                    return "до 27,5 кг"
                elif weight <= 30:
                    return "до 30 кг"
                elif weight <= 32.5:
                    return "до 32,5 кг"
                elif weight <= 35:
                    return "до 35 кг"
                elif weight <= 37.5:
                    return "до 37,5 кг"
                elif weight <= 40:
                    return "до 40 кг"
                else:
                    return "свыше 40 кг"
            else:  # Девочки
                if weight <= 20:
                    return "до 20 кг"
                elif weight <= 25:
                    return "до 25 кг"
                elif weight <= 30:
                    return "до 30 кг"
                elif weight <= 35:
                    return "до 35 кг"
                else:
                    return "свыше 35 кг"

        # 10-11 лет
        elif 10 <= age <= 11:
            if self.gender == 'M':  # Мальчики
                if weight <= 30:
                    return "до 30 кг"
                elif weight <= 35:
                    return "до 35 кг"
                elif weight <= 40:
                    return "до 40 кг"
                elif weight <= 45:
                    return "до 45 кг"
                else:
                    return "свыше 45 кг"
            else:  # Девочки
                if weight <= 25:
                    return "до 25 кг"
                elif weight <= 30:
                    return "до 30 кг"
                elif weight <= 35:
                    return "до 35 кг"
                elif weight <= 40:
                    return "до 40 кг"
                else:
                    return "свыше 40 кг"

        # 12-13 лет
        elif 12 <= age <= 13:
            if self.gender == 'M':  # Юноши
                if weight <= 35:
                    return "до 35 кг"
                elif weight <= 40:
                    return "до 40 кг"
                elif weight <= 45:
                    return "до 45 кг"
                elif weight <= 50:
                    return "до 50 кг"
                elif weight <= 55:
                    return "до 55 кг"
                else:
                    return "свыше 55 кг"
            else:  # Девушки
                if weight <= 35:
                    return "до 35 кг"
                elif weight <= 40:
                    return "до 40 кг"
                elif weight <= 45:
                    return "до 45 кг"
                elif weight <= 50:
                    return "до 50 кг"
                else:
                    return "свыше 50 кг"

        # 14-15 лет
        elif 14 <= age <= 15:
            if self.gender == 'M':  # Юноши
                if weight <= 45:
                    return "до 45 кг"
                elif weight <= 50:
                    return "до 50 кг"
                elif weight <= 55:
                    return "до 55 кг"
                elif weight <= 60:
                    return "до 60 кг"
                elif weight <= 65:
                    return "до 65 кг"
                else:
                    return "свыше 65 кг"
            else:  # Девушки
                if weight <= 45:
                    return "до 45 кг"
                elif weight <= 50:
                    return "до 50 кг"
                elif weight <= 55:
                    return "до 55 кг"
                elif weight <= 60:
                    return "до 60 кг"
                else:
                    return "свыше 60 кг"

        # 16-17 лет
        elif 16 <= age <= 17:
            if self.gender == 'M':  # Юниоры
                if weight <= 60:
                    return "до 60 кг"
                elif weight <= 65:
                    return "до 65 кг"
                elif weight <= 70:
                    return "до 70 кг"
                elif weight <= 75:
                    return "до 75 кг"
                else:
                    return "свыше 75 кг"
            else:  # Юниорки
                if weight <= 55:
                    return "до 55 кг"
                elif weight <= 60:
                    return "до 60 кг"
                else:
                    return "свыше 60 кг"

        # 18 лет и старше
        elif age >= 18:
            if self.gender == 'M':  # Мужчины
                if weight <= 70:
                    return "до 70 кг"
                elif weight <= 80:
                    return "до 80 кг"
                elif weight <= 90:
                    return "до 90 кг"
                else:
                    return "свыше 90 кг"
            else:  # Женщины
                if weight <= 60:
                    return "до 60 кг"
                elif weight <= 70:
                    return "до 70 кг"
                else:
                    return "свыше 70 кг"

        return "Не определена"


class Match(models.Model):
    """Поединок"""
    STATUS_CHOICES = [
        ('scheduled', 'Запланирован'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершен'),
        ('walkover', 'Неявка'),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнир")
    age_category = models.CharField(max_length=20, verbose_name="Возрастная категория")
    weight_category = models.CharField(max_length=50, verbose_name="Весовая категория")
    gender = models.CharField(max_length=1, choices=Participant.GENDER_CHOICES, verbose_name="Пол")

    round_name = models.CharField(max_length=50, verbose_name="Раунд", default="1/8")
    round_number = models.IntegerField(default=1, verbose_name="Номер раунда")

    participant1 = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True,
                                     related_name='matches_as_p1', verbose_name="Участник 1")
    participant2 = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True,
                                     related_name='matches_as_p2', verbose_name="Участник 2")

    winner = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='matches_won', verbose_name="Победитель")

    score_p1 = models.IntegerField(default=0, verbose_name="Счет участника 1")
    score_p2 = models.IntegerField(default=0, verbose_name="Счет участника 2")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="Статус")
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='previous_matches', verbose_name="Следующий матч")

    # Связь с боем за 3 место
    third_place_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='third_place_sources', verbose_name="Бой за 3 место")

    match_order = models.IntegerField(default=0, verbose_name="Порядок матча")
    is_third_place_match = models.BooleanField(default=False, verbose_name="Бой за 3 место")

    class Meta:
        verbose_name = "Поединок"
        verbose_name_plural = "Поединки"
        ordering = ['age_category', 'gender', 'weight_category', 'round_number', 'match_order']

    def __str__(self):
        p1 = self.participant1.last_name if self.participant1 else "TBD"
        p2 = self.participant2.last_name if self.participant2 else "TBD"
        return f"{p1} vs {p2} - {self.round_name}"