import math
import random
from .models import Participant, Match


def get_unique_categories(tournament):
    """Получение уникальных комбинаций категорий"""
    participants = Participant.objects.filter(tournament=tournament)

    categories = set()
    for p in participants:
        if p.age_category and p.weight_category:  # Проверяем, что категории определены
            categories.add((p.age_category, p.gender, p.weight_category))

    return sorted(list(categories))


def generate_bracket_for_category(tournament, age_category, gender, weight_category):
    """
    Генерация олимпийской сетки для конкретной категории
    """
    print(f"Генерация сетки для: {age_category}, {gender}, {weight_category}")

    # Получаем участников категории
    participants = list(Participant.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ))

    print(f"Найдено участников: {len(participants)}")

    if len(participants) < 2:
        print("Недостаточно участников")
        return False

    # Перемешиваем для случайной жеребьевки
    random.shuffle(participants)

    # Удаляем старые матчи для этой категории
    deleted = Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ).delete()

    print(f"Удалено старых матчей: {deleted}")

    num_participants = len(participants)

    # Определяем количество раундов
    total_rounds = math.ceil(math.log2(num_participants))

    # Определяем количество матчей в первом раунде
    first_round_matches = 2 ** (total_rounds - 1)

    print(f"Всего раундов: {total_rounds}, матчей в первом раунде: {first_round_matches}")

    # Создаем названия раундов
    if first_round_matches == 8:
        round_names = {1: "1/8", 2: "1/4", 3: "1/2", 4: "Финал"}
    elif first_round_matches == 4:
        round_names = {1: "1/4", 2: "1/2", 3: "Финал"}
    elif first_round_matches == 2:
        round_names = {1: "1/2", 2: "Финал"}
    else:
        round_names = {}
        for i in range(1, total_rounds + 1):
            if i == total_rounds:
                round_names[i] = "Финал"
            elif i == total_rounds - 1:
                round_names[i] = "1/2"
            elif i == total_rounds - 2:
                round_names[i] = "1/4"
            else:
                round_names[i] = f"1/{2 ** (total_rounds - i + 1)}"

    matches = []
    match_order = 0

    # Создаем матчи первого раунда
    for i in range(first_round_matches):
        match = Match(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category,
            round_number=1,
            round_name=round_names.get(1, f"1/{first_round_matches * 2}"),
            match_order=match_order
        )

        # Распределяем участников
        if i * 2 < num_participants:
            match.participant1 = participants[i * 2]
        if i * 2 + 1 < num_participants:
            match.participant2 = participants[i * 2 + 1]

        match.save()
        print(f"Создан матч 1 раунда: {match}")
        matches.append(match)
        match_order += 1

    # Создаем следующие раунды
    current_round_matches = matches
    round_num = 1

    while len(current_round_matches) > 1:
        next_round_matches = []
        round_num += 1

        for i in range(0, len(current_round_matches), 2):
            # Создаем матч следующего раунда
            next_match = Match(
                tournament=tournament,
                age_category=age_category,
                gender=gender,
                weight_category=weight_category,
                round_number=round_num,
                round_name=round_names.get(round_num, f"Раунд {round_num}"),
                match_order=match_order
            )
            next_match.save()
            print(f"Создан матч {round_num} раунда: {next_match}")

            # Связываем предыдущие матчи
            if i < len(current_round_matches):
                current_round_matches[i].next_match = next_match
                current_round_matches[i].save()

            if i + 1 < len(current_round_matches):
                current_round_matches[i + 1].next_match = next_match
                current_round_matches[i + 1].save()

            next_round_matches.append(next_match)
            match_order += 1

        current_round_matches = next_round_matches

    # Создаем бой за 3 место, если есть полуфиналы
    if round_num >= 3:  # Если есть полуфиналы
        third_place_match = Match(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category,
            round_number=round_num + 1,
            round_name="Бой за 3 место",
            match_order=match_order,
            is_third_place_match=True
        )
        third_place_match.save()
        print(f"Создан бой за 3 место: {third_place_match}")

    print(
        f"Генерация завершена. Всего матчей: {Match.objects.filter(tournament=tournament, age_category=age_category, gender=gender, weight_category=weight_category).count()}")
    return True


def get_category_stats(tournament):
    """Получение статистики по категориям"""
    participants = Participant.objects.filter(tournament=tournament)

    stats = {}
    for p in participants:
        if p.age_category and p.weight_category:  # Проверяем, что категории определены
            key = f"{p.age_category}|{p.get_gender_display()}|{p.weight_category}"
            if key not in stats:
                stats[key] = {
                    'age_category': p.age_category,
                    'gender': p.get_gender_display(),
                    'gender_code': p.gender,
                    'weight_category': p.weight_category,
                    'count': 0,
                    'participants': []
                }
            stats[key]['count'] += 1
            stats[key]['participants'].append(p)

    return stats


def process_excel_file(excel_file, tournament, clear_existing=False):
    """
    Обработка Excel файла с участниками
    """
    import pandas as pd
    from datetime import datetime

    try:
        # Читаем Excel файл
        df = pd.read_excel(excel_file)

        # Проверяем наличие необходимых колонок
        required_columns = ['Фамилия', 'Имя', 'Дата рождения', 'Пол', 'Вес', 'Клуб']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                'success': False,
                'error': f'Отсутствуют колонки: {", ".join(missing_columns)}'
            }

        # Очищаем существующих участников если нужно
        if clear_existing:
            Participant.objects.filter(tournament=tournament).delete()

        # Обрабатываем каждую строку
        imported = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Преобразуем дату рождения
                birth_date = row['Дата рождения']
                if isinstance(birth_date, str):
                    try:
                        birth_date = datetime.strptime(birth_date, '%d.%m.%Y').date()
                    except:
                        try:
                            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                        except:
                            birth_date = datetime.strptime(birth_date, '%d.%m.%y').date()
                elif isinstance(birth_date, pd.Timestamp):
                    birth_date = birth_date.date()

                # Преобразуем пол
                gender = str(row['Пол']).upper().strip()
                if gender in ['М', 'M', 'МУЖ', 'MALE', 'МУЖСКОЙ', 'МУЖЧИНА']:
                    gender = 'M'
                elif gender in ['Ж', 'F', 'ЖЕН', 'FEMALE', 'ЖЕНСКИЙ', 'ЖЕНЩИНА']:
                    gender = 'F'
                else:
                    raise ValueError(f'Некорректное значение пола: {row["Пол"]}')

                # Создаем участника
                participant = Participant(
                    tournament=tournament,
                    last_name=str(row['Фамилия']).strip(),
                    first_name=str(row['Имя']).strip(),
                    birth_date=birth_date,
                    gender=gender,
                    weight=float(row['Вес']),
                    club=str(row['Клуб']).strip(),
                    coach=str(row.get('Тренер', '')).strip() if pd.notna(row.get('Тренер')) else '',
                    source_file=excel_file.name,
                    row_number=index + 2
                )
                participant.save()
                imported += 1

            except Exception as e:
                errors.append(f'Строка {index + 2}: {str(e)}')

        return {
            'success': True,
            'imported': imported,
            'errors': errors
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Ошибка при чтении файла: {str(e)}'
        }