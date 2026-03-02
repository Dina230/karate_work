import math
import random
from collections import defaultdict
from .models import Participant, Match


def get_unique_categories(tournament):
    """Получение уникальных комбинаций категорий"""
    participants = Participant.objects.filter(tournament=tournament)

    categories = set()
    for p in participants:
        if p.age_category and p.weight_category:
            categories.add((p.age_category, p.gender, p.weight_category))

    return sorted(list(categories))


def distribute_participants_by_club(participants):
    """
    Распределяет участников по турнирной сетке так, чтобы представители одного клуба
    НЕ встречались в первых раундах. В финале встреча допустима.

    Использует стандартный турнирный посев с разведением по разным половинам.
    """
    if len(participants) <= 2:
        return participants

    # Группируем участников по клубам
    clubs = defaultdict(list)
    for p in participants:
        clubs[p.club].append(p)

    # Сортируем клубы по количеству участников (от большего к меньшему)
    sorted_clubs = sorted(clubs.items(), key=lambda x: len(x[1]), reverse=True)

    # Определяем размер сетки (ближайшая степень двойки)
    total = len(participants)
    bracket_size = 2 ** math.ceil(math.log2(total))

    print(f"\nРаспределение {total} участников в сетку размером {bracket_size}")
    print("Клубы:")
    for club, members in sorted_clubs:
        print(f"  {club}: {len(members)} участников")

    # Создаем пустые слоты
    bracket = [None] * bracket_size

    # Генерируем позиции для максимального разведения
    # Сначала заполняем нечетные позиции, потом четные
    positions = []

    # Берем позиции через одну, начиная с 0
    half = bracket_size // 2
    for i in range(half):
        positions.append(i * 2)  # Четные: 0, 2, 4, 6...

    for i in range(half):
        positions.append(i * 2 + 1)  # Нечетные: 1, 3, 5, 7...

    # Ограничиваем количество позиций
    positions = positions[:total]
    positions.sort()

    print(f"Позиции для размещения: {positions}")

    # Размещаем участников по принципу "каждый клуб получает разные половины"
    current_pos_index = 0

    # Сначала размещаем по одному участнику от каждого клуба в разные половины
    half_point = bracket_size // 2

    # Отслеживаем, в какие половины уже попали клубы
    club_positions = {}

    for club, members in sorted_clubs:
        club_positions[club] = {'left': 0, 'right': 0}

    # Размещаем участников
    remaining_positions = positions.copy()

    # Сначала пытаемся разместить по одному участнику от каждого клуба
    for round_num in range(max(len(m) for club, m in sorted_clubs)):
        for club, members in sorted_clubs:
            if round_num < len(members):
                # Ищем позицию в другой половине, чем предыдущие участники этого клуба
                if remaining_positions:
                    # Просто берем следующую позицию
                    pos = remaining_positions.pop(0)
                    bracket[pos] = members[round_num]

                    # Отмечаем, в какой половине размещен участник
                    if pos < half_point:
                        club_positions[club]['left'] += 1
                    else:
                        club_positions[club]['right'] += 1

                    print(f"  {members[round_num].last_name} ({club}) -> позиция {pos}")

    # Проверяем коллизии в первом раунде
    print("\nПроверка коллизий в первом раунде:")
    collisions = 0

    for i in range(0, bracket_size, 2):
        if i + 1 < bracket_size:
            p1 = bracket[i]
            p2 = bracket[i + 1]
            if p1 and p2 and p1.club == p2.club:
                collisions += 1
                print(f"  Коллизия в позициях {i} и {i + 1}: {p1.club}")

                # Ищем замену в других позициях
                for j in range(bracket_size):
                    if j != i and j != i + 1 and bracket[j] and bracket[j].club != p1.club:
                        # Меняем местами
                        bracket[i + 1], bracket[j] = bracket[j], bracket[i + 1]
                        print(f"    Исправлено: обмен с позицией {j}")
                        break

    if collisions == 0:
        print("  Коллизий не найдено")

    # Убираем пустые слоты и возвращаем только реальных участников
    result = [p for p in bracket if p is not None]

    print(f"\nИтоговый порядок участников ({len(result)}):")
    for i, p in enumerate(result):
        print(f"  {i + 1}. {p.last_name} {p.first_name} ({p.club})")

    return result


def generate_bracket_for_category(tournament, age_category, gender, weight_category):
    """
    Генерация олимпийской сетки для конкретной категории
    """
    print(f"\n{'=' * 50}")
    print(f"Генерация сетки для: {age_category}, {gender}, {weight_category}")
    print('=' * 50)

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

    # Распределяем участников по клубам
    participants = distribute_participants_by_club(participants)

    # Удаляем старые матчи
    deleted = Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ).delete()

    print(f"Удалено старых матчей")

    num_participants = len(participants)

    # Определяем количество раундов
    total_rounds = math.ceil(math.log2(num_participants))
    print(f"Всего раундов: {total_rounds}")

    # Создаем названия раундов
    round_names = {}
    for i in range(1, total_rounds + 1):
        if i == total_rounds:
            round_names[i] = "Финал"
        elif i == total_rounds - 1:
            round_names[i] = "1/2"
        elif i == total_rounds - 2:
            round_names[i] = "1/4"
        else:
            power = 2 ** (total_rounds - i + 1)
            round_names[i] = f"1/{power}"

    print("Названия раундов:", round_names)

    matches_by_round = {}
    match_order = 0

    # Первый раунд
    first_round_matches = []
    num_first_round = 2 ** (total_rounds - 1)

    print(f"\nСоздание первого раунда ({num_first_round} матчей):")

    for i in range(num_first_round):
        match = Match(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category,
            round_number=1,
            round_name=round_names[1],
            match_order=match_order
        )

        # Распределяем участников
        if i * 2 < num_participants:
            match.participant1 = participants[i * 2]
        if i * 2 + 1 < num_participants:
            match.participant2 = participants[i * 2 + 1]

        match.save()
        first_round_matches.append(match)
        match_order += 1

        p1 = match.participant1.last_name if match.participant1 else "TBD"
        p2 = match.participant2.last_name if match.participant2 else "TBD"
        p1_club = match.participant1.club if match.participant1 else "?"
        p2_club = match.participant2.club if match.participant2 else "?"
        print(f"  Матч {i + 1}: {p1} ({p1_club}) vs {p2} ({p2_club})")

    matches_by_round[1] = first_round_matches

    # Следующие раунды
    current_round_matches = first_round_matches
    semi_finals = []

    for round_num in range(2, total_rounds + 1):
        next_round_matches = []
        print(f"\nСоздание {round_num} раунда ({round_names[round_num]}):")

        for i in range(0, len(current_round_matches), 2):
            # Создаем матч следующего раунда
            match = Match(
                tournament=tournament,
                age_category=age_category,
                gender=gender,
                weight_category=weight_category,
                round_number=round_num,
                round_name=round_names[round_num],
                match_order=match_order
            )
            match.save()

            # Связываем с предыдущими матчами
            if i < len(current_round_matches):
                current_round_matches[i].next_match = match
                current_round_matches[i].save()

            if i + 1 < len(current_round_matches):
                current_round_matches[i + 1].next_match = match
                current_round_matches[i + 1].save()

            next_round_matches.append(match)
            match_order += 1

            print(f"  Матч {i // 2 + 1}: создан")

        # Запоминаем полуфиналы
        if round_names[round_num] == "1/2":
            semi_finals = next_round_matches.copy()
            print(f"  Запомнены полуфиналы: {len(semi_finals)} матчей")

        matches_by_round[round_num] = next_round_matches
        current_round_matches = next_round_matches

    # Создаем бой за 3 место
    if semi_finals:
        print(f"\nСоздание боя за 3 место:")

        third_place_match = Match(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category,
            round_number=total_rounds + 1,
            round_name="Бой за 3 место",
            match_order=match_order,
            is_third_place_match=True
        )
        third_place_match.save()
        print(f"  Бой за 3 место создан")

        # Связываем полуфиналы с боем за 3 место
        for i, semi in enumerate(semi_finals):
            semi.third_place_match = third_place_match
            semi.save()
            print(f"  Полуфинал {i + 1} связан с боем за 3 место")

    total_matches = Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ).count()

    print(f"\nГенерация завершена. Всего матчей: {total_matches}")
    return True


def get_category_stats(tournament):
    """Получение статистики по категориям"""
    participants = Participant.objects.filter(tournament=tournament)

    stats = {}
    for p in participants:
        if p.age_category and p.weight_category:
            key = f"{p.age_category}|{p.get_gender_display()}|{p.weight_category}"
            if key not in stats:
                stats[key] = {
                    'age_category': p.age_category,
                    'gender': p.get_gender_display(),
                    'gender_code': p.gender,
                    'weight_category': p.weight_category,
                    'count': 0,
                    'participants': [],
                    'clubs': set()
                }
            stats[key]['count'] += 1
            stats[key]['participants'].append(p)
            stats[key]['clubs'].add(p.club)

    for key in stats:
        stats[key]['clubs'] = list(stats[key]['clubs'])
        stats[key]['unique_clubs'] = len(stats[key]['clubs'])

    return stats


def process_excel_file(excel_file, tournament, clear_existing=False):
    """
    Обработка Excel файла с участниками
    """
    import pandas as pd
    from datetime import datetime

    try:
        df = pd.read_excel(excel_file)

        required_columns = ['Фамилия', 'Имя', 'Дата рождения', 'Пол', 'Вес', 'Клуб']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                'success': False,
                'error': f'Отсутствуют колонки: {", ".join(missing_columns)}'
            }

        if clear_existing:
            Participant.objects.filter(tournament=tournament).delete()

        imported = 0
        errors = []

        for index, row in df.iterrows():
            try:
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

                gender = str(row['Пол']).upper().strip()
                if gender in ['М', 'M', 'МУЖ', 'MALE', 'МУЖСКОЙ', 'МУЖЧИНА']:
                    gender = 'M'
                elif gender in ['Ж', 'F', 'ЖЕН', 'FEMALE', 'ЖЕНСКИЙ', 'ЖЕНЩИНА']:
                    gender = 'F'
                else:
                    raise ValueError(f'Некорректное значение пола: {row["Пол"]}')

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