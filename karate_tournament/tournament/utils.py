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
    Распределяет участников по турнирной сетке
    """
    if len(participants) <= 2:
        return participants

    # Группируем по клубам
    clubs = defaultdict(list)
    for p in participants:
        clubs[p.club].append(p)

    # Сортируем клубы по количеству участников
    sorted_clubs = sorted(clubs.items(), key=lambda x: len(x[1]), reverse=True)

    total = len(participants)
    bracket_size = 2 ** math.ceil(math.log2(total))

    # Стандартные позиции для турнирной сетки
    def get_seed_positions(size):
        if size == 2:
            return [0, 1]
        elif size == 4:
            return [0, 3, 1, 2]
        elif size == 8:
            return [0, 7, 3, 4, 1, 6, 2, 5]
        elif size == 16:
            return [0, 15, 7, 8, 3, 12, 4, 11, 1, 14, 6, 9, 2, 13, 5, 10]
        else:
            return list(range(size))

    positions = get_seed_positions(bracket_size)[:total]
    positions.sort()

    bracket = [None] * bracket_size
    idx = 0

    # Размещаем участников
    for _, members in sorted_clubs:
        for member in members:
            if idx < len(positions):
                bracket[positions[idx]] = member
                idx += 1

    # Исправляем коллизии (одинаковые клубы в одном матче)
    for i in range(0, bracket_size, 2):
        if i + 1 < bracket_size:
            p1, p2 = bracket[i], bracket[i + 1]
            if p1 and p2 and p1.club == p2.club:
                for j in range(i + 2, bracket_size):
                    if bracket[j] and bracket[j].club != p1.club:
                        bracket[i + 1], bracket[j] = bracket[j], bracket[i + 1]
                        break

    return [p for p in bracket if p is not None]


def generate_bracket_for_category(tournament, age_category, gender, weight_category):
    """
    Генерация олимпийской сетки для любого количества участников
    """
    print(f"\n{'=' * 50}")
    print(f"Генерация сетки для: {age_category}, {gender}, {weight_category}")

    participants = list(Participant.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ))

    n = len(participants)
    print(f"Участников: {n}")

    if n < 2:
        return False

    # Распределяем участников
    participants = distribute_participants_by_club(participants)

    # Удаляем старые матчи
    Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ).delete()

    # Определяем размер полной сетки (ближайшая степень двойки)
    full_size = 2 ** math.ceil(math.log2(n))
    byes = full_size - n

    print(f"Размер полной сетки: {full_size}, BYE: {byes}")

    # Количество раундов
    total_rounds = int(math.log2(full_size))
    print(f"Всего раундов: {total_rounds}")

    # Названия раундов
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

    all_matches = []
    match_order = 0

    # ПЕРВЫЙ РАУНД
    first_round = []
    matches_in_first = full_size // 2

    print(f"\nПервый раунд: {matches_in_first} матчей")

    # Количество реальных матчей (с двумя участниками)
    real_matches = (n - byes) // 2
    # Количество BYE матчей (с одним участником)
    bye_matches = byes

    print(f"  Реальных матчей: {real_matches}")
    print(f"  BYE матчей: {bye_matches}")

    p_idx = 0

    for i in range(matches_in_first):
        match = Match(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category,
            round_number=1,
            round_name=round_names[1],
            match_order=match_order
        )

        if i < real_matches:
            # Реальный матч с двумя участниками
            match.participant1 = participants[p_idx]
            p_idx += 1
            match.participant2 = participants[p_idx]
            p_idx += 1
            match.save()
            first_round.append(match)
            print(f"  Матч {i + 1}: {match.participant1.last_name} vs {match.participant2.last_name}")
        else:
            # BYE матч - только один участник автоматически проходит
            if p_idx < n:
                match.participant1 = participants[p_idx]
                p_idx += 1
                match.winner = match.participant1
                match.status = 'completed'
                match.save()
                first_round.append(match)
                print(f"  Матч {i + 1}: {match.participant1.last_name} vs BYE (автопроход)")

        all_matches.append(match)
        match_order += 1

    # СЛЕДУЮЩИЕ РАУНДЫ
    current_round = first_round
    semi_finals = []

    for round_num in range(2, total_rounds + 1):
        next_round = []
        matches_in_round = len(current_round) // 2

        print(f"\nРаунд {round_num} ({round_names[round_num]}): {matches_in_round} матчей")

        for i in range(matches_in_round):
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
            all_matches.append(match)
            match_order += 1

            # Связываем с предыдущими матчами
            left_idx = i * 2
            right_idx = i * 2 + 1

            if left_idx < len(current_round):
                current_round[left_idx].next_match = match
                current_round[left_idx].save()

            if right_idx < len(current_round):
                current_round[right_idx].next_match = match
                current_round[right_idx].save()

            next_round.append(match)

            # Если левый матч уже завершен (BYE), автоматически добавляем победителя
            if left_idx < len(current_round) and current_round[left_idx].status == 'completed' and current_round[
                left_idx].winner:
                if not match.participant1:
                    match.participant1 = current_round[left_idx].winner
                    match.save()
                    print(f"    → {current_round[left_idx].winner.last_name} добавлен в матч")

            # Если правый матч уже завершен (BYE), автоматически добавляем победителя
            if right_idx < len(current_round) and current_round[right_idx].status == 'completed' and current_round[
                right_idx].winner:
                if not match.participant2 and match.participant1 != current_round[right_idx].winner:
                    match.participant2 = current_round[right_idx].winner
                    match.save()
                    print(f"    → {current_round[right_idx].winner.last_name} добавлен в матч")

        # Запоминаем полуфиналы
        if round_names[round_num] == "1/2":
            semi_finals = next_round.copy()
            print(f"  → Полуфиналы: {len(semi_finals)} матчей")

        current_round = next_round

    # БОЙ ЗА 3 МЕСТО (только если есть полуфиналы и участников достаточно)
    if semi_finals and len(semi_finals) >= 2 and total_rounds >= 3:
        print(f"\nСоздание боя за 3 место")

        third_match = Match(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category,
            round_number=total_rounds + 1,
            round_name="Бой за 3 место",
            match_order=match_order,
            is_third_place_match=True
        )
        third_match.save()
        all_matches.append(third_match)

        # Связываем полуфиналы с боем за 3 место
        for i, semi in enumerate(semi_finals):
            semi.third_place_match = third_match
            semi.save()
            print(f"  Полуфинал {i + 1} связан с боем за 3 место")

    print(f"\nГенерация завершена. Всего матчей: {len(all_matches)}")
    return True


def get_category_stats(tournament):
    """Статистика по категориям"""
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

    # Добавляем информацию о матчах
    from django.db.models import Count, Q
    for key, data in stats.items():
        age = data['age_category']
        gender = data['gender_code']
        weight = data['weight_category']

        matches = Match.objects.filter(
            tournament=tournament,
            age_category=age,
            gender=gender,
            weight_category=weight
        )

        data['total_matches'] = matches.count()
        data['completed_matches'] = matches.filter(status='completed').count()
        data['pending_matches'] = matches.filter(status__in=['scheduled', 'in_progress']).count()
        data['has_matches'] = data['total_matches'] > 0
        data['all_matches_completed'] = data['total_matches'] > 0 and data['completed_matches'] == data['total_matches']

    # Преобразуем set в список для шаблона
    for key in stats:
        stats[key]['clubs'] = list(stats[key]['clubs'])
        stats[key]['unique_clubs'] = len(stats[key]['clubs'])

    return stats


def process_excel_file(excel_file, tournament, clear_existing=False):
    """Обработка Excel файла"""
    import pandas as pd
    from datetime import datetime

    try:
        df = pd.read_excel(excel_file)

        required = ['Фамилия', 'Имя', 'Дата рождения', 'Пол', 'Вес', 'Клуб']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return {'success': False, 'error': f'Нет колонок: {missing}'}

        if clear_existing:
            Participant.objects.filter(tournament=tournament).delete()

        imported = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                # Дата
                bd = row['Дата рождения']
                if isinstance(bd, str):
                    try:
                        birth = datetime.strptime(bd, '%d.%m.%Y').date()
                    except:
                        birth = datetime.strptime(bd, '%Y-%m-%d').date()
                elif isinstance(bd, pd.Timestamp):
                    birth = bd.date()
                else:
                    continue

                # Пол
                g = str(row['Пол']).upper().strip()
                gender = 'M' if g in ['М', 'M', 'МУЖ', 'МУЖСКОЙ'] else 'F'

                # Клуб
                club = str(row['Клуб']).strip()

                # Вес
                weight = float(row['Вес']) if isinstance(row['Вес'], (int, float)) else float(
                    str(row['Вес']).replace(',', '.'))

                Participant.objects.create(
                    tournament=tournament,
                    last_name=str(row['Фамилия']).strip(),
                    first_name=str(row['Имя']).strip(),
                    birth_date=birth,
                    gender=gender,
                    weight=weight,
                    club=club,
                    coach=str(row.get('Тренер', '')).strip() if pd.notna(row.get('Тренер')) else '',
                    source_file=excel_file.name,
                    row_number=idx + 2
                )
                imported += 1

            except Exception as e:
                errors.append(f'Строка {idx + 2}: {str(e)}')

        return {'success': True, 'imported': imported, 'errors': errors}

    except Exception as e:
        return {'success': False, 'error': str(e)}