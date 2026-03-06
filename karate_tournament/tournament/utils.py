import math
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


def distribute_participants_smart(participants):
    """
    Умное распределение участников с гарантией, что участники
    одного тренера НЕ встретятся в первом раунде
    """
    if len(participants) <= 2:
        return participants

    total = len(participants)
    bracket_size = 2 ** math.ceil(math.log2(total))

    # Группируем по тренерам
    coaches = defaultdict(list)
    for p in participants:
        coach_key = p.coach if p.coach else "Без тренера"
        coaches[coach_key].append(p)

    # Сортируем тренеров по количеству участников (от большего к меньшему)
    sorted_coaches = sorted(coaches.items(), key=lambda x: len(x[1]), reverse=True)

    # Стандартные позиции для олимпийской сетки (правильный посев)
    def get_seed_positions(size):
        """Генерирует позиции для правильного посева в олимпийской сетке"""
        if size == 2:
            return [0, 1]

        positions = [0, 1]
        current_size = 2

        while current_size < size:
            new_positions = []
            for pos in positions:
                new_positions.append(pos * 2)
                new_positions.append(pos * 2 + 1)
            positions = new_positions
            current_size *= 2

        return positions

    seed_positions = get_seed_positions(bracket_size)

    # Создаем пустую сетку
    bracket = [None] * bracket_size

    # Размещаем участников по принципу максимального разведения
    placed_count = 0

    # Сначала размещаем по одному участнику от каждого тренера
    max_in_group = max(len(members) for _, members in sorted_coaches) if sorted_coaches else 0

    for round_num in range(max_in_group):
        for coach, members in sorted_coaches:
            if round_num < len(members):
                member = members[round_num]

                # Ищем лучшую позицию для этого участника
                best_pos = None

                for pos in seed_positions:
                    if bracket[pos] is not None:
                        continue

                    # Проверяем, кто будет соперником в первом раунде
                    if pos % 2 == 0:
                        opponent_pos = pos + 1
                    else:
                        opponent_pos = pos - 1

                    # Проверяем соперника
                    if opponent_pos < bracket_size and bracket[opponent_pos] is not None:
                        opponent = bracket[opponent_pos]
                        # Если соперник от того же тренера - пропускаем
                        if opponent.coach == member.coach and member.coach:
                            continue
                        # Если соперник из того же клуба - пропускаем
                        if opponent.club == member.club:
                            continue

                    best_pos = pos
                    break

                if best_pos is not None:
                    bracket[best_pos] = member
                    placed_count += 1

    # Возвращаем только заполненные позиции
    result = [p for p in bracket if p is not None]
    return result


def generate_bracket_for_category(tournament, age_category, gender, weight_category):
    """
    Генерация олимпийской сетки для любой категории
    """
    print(f"\n{'=' * 50}")
    print(f"Генерация сетки для: {age_category}, {gender}, {weight_category}")

    participants = list(Participant.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ).order_by('last_name'))

    n = len(participants)
    print(f"Участников: {n}")

    if n < 2:
        return False

    # Удаляем старые матчи
    Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender,
        weight_category=weight_category
    ).delete()

    # Распределяем участников с учетом тренера и клуба
    participants = distribute_participants_smart(participants)

    # Определяем размер полной сетки (ближайшая степень двойки)
    full_size = 2 ** math.ceil(math.log2(n))
    byes = full_size - n

    print(f"Размер полной сетки: {full_size}, BYE: {byes}")

    # Количество раундов
    total_rounds = int(math.log2(full_size))

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

    # Создаем структуру для хранения матчей по раундам
    rounds_matches = {i: [] for i in range(1, total_rounds + 1)}

    # ПЕРВЫЙ РАУНД
    matches_in_first = full_size // 2
    real_matches = (n - byes) // 2 if n > byes else 0
    bye_matches = byes

    print(f"Первый раунд: {matches_in_first} матчей")
    print(f"Реальных матчей: {real_matches}, BYE матчей: {bye_matches}")

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

        if i < real_matches and p_idx + 1 < len(participants):
            # Реальный матч с двумя участниками
            match.participant1 = participants[p_idx]
            match.participant2 = participants[p_idx + 1]
            p_idx += 2
            match.save()
            rounds_matches[1].append(match)

            p1_name = match.participant1.last_name if match.participant1 else "TBD"
            p2_name = match.participant2.last_name if match.participant2 else "TBD"
            print(f"  Матч {i + 1}: {p1_name} vs {p2_name}")

        elif p_idx < len(participants):
            # BYE матч - один участник автоматически проходит
            match.participant1 = participants[p_idx]
            p_idx += 1
            match.winner = match.participant1
            match.status = 'completed'
            match.score_p1 = 0
            match.score_p2 = 0
            match.save()
            rounds_matches[1].append(match)

            print(f"  Матч {i + 1}: {match.participant1.last_name} vs BYE (автопроход)")
        else:
            # Оба участника TBD (для полноты сетки)
            match.save()
            rounds_matches[1].append(match)

        all_matches.append(match)
        match_order += 1

    # СЛЕДУЮЩИЕ РАУНДЫ
    for round_num in range(2, total_rounds + 1):
        prev_round_matches = rounds_matches[round_num - 1]
        matches_in_round = len(prev_round_matches) // 2

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
            rounds_matches[round_num].append(match)
            all_matches.append(match)
            match_order += 1

            # Связываем с предыдущими матчами
            left_idx = i * 2
            right_idx = i * 2 + 1

            if left_idx < len(prev_round_matches):
                prev_round_matches[left_idx].next_match = match
                prev_round_matches[left_idx].save()

                # Если предыдущий матч уже завершен (BYE), добавляем победителя
                if prev_round_matches[left_idx].status == 'completed' and prev_round_matches[left_idx].winner:
                    match.participant1 = prev_round_matches[left_idx].winner
                    match.save()

            if right_idx < len(prev_round_matches):
                prev_round_matches[right_idx].next_match = match
                prev_round_matches[right_idx].save()

                # Если предыдущий матч уже завершен (BYE), добавляем победителя
                if prev_round_matches[right_idx].status == 'completed' and prev_round_matches[right_idx].winner:
                    if match.participant1 != prev_round_matches[right_idx].winner:
                        match.participant2 = prev_round_matches[right_idx].winner
                        match.save()

            print(f"  Матч {i + 1}: создан")

    # БОЙ ЗА 3 МЕСТО (только если есть полуфиналы - минимум 4 участника)
    if total_rounds >= 2:
        semi_finals = rounds_matches.get(total_rounds - 1, [])

        if len(semi_finals) >= 2:
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
            key = f"{p.age_category}|{p.gender}|{p.weight_category}"

            if key not in stats:
                stats[key] = {
                    'age_category': p.age_category,
                    'gender': p.get_gender_display(),
                    'gender_code': p.gender,
                    'weight_category': p.weight_category,
                    'count': 0,
                    'participants': [],
                    'clubs': set(),
                    'coaches': set()
                }

            stats[key]['count'] += 1
            stats[key]['participants'].append(p)
            stats[key]['clubs'].add(p.club)
            if p.coach:
                stats[key]['coaches'].add(p.coach)

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
        stats[key]['coaches'] = list(stats[key]['coaches'])
        stats[key]['unique_coaches'] = len(stats[key]['coaches'])

    return stats


def process_excel_file(excel_file, tournament, clear_existing=False):
    """
    Обработка Excel файла с участниками
    """
    import pandas as pd
    from datetime import datetime
    import re

    try:
        df = pd.read_excel(excel_file)

        # Проверяем наличие необходимых колонок
        required = ['Фамилия', 'Имя', 'Дата рождения', 'Пол', 'Клуб']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return {'success': False, 'error': f'Отсутствуют колонки: {missing}'}

        if clear_existing:
            Participant.objects.filter(tournament=tournament).delete()

        imported = 0
        errors = []
        skipped = 0

        for idx, row in df.iterrows():
            try:
                # Проверяем, что строка не пустая
                if pd.isna(row['Фамилия']) or pd.isna(row['Имя']):
                    skipped += 1
                    continue

                # Обработка даты рождения
                birth_date = None
                if pd.notna(row['Дата рождения']):
                    bd = row['Дата рождения']
                    if isinstance(bd, str):
                        try:
                            birth_date = datetime.strptime(bd, '%Y-%m-%d').date()
                        except:
                            try:
                                birth_date = datetime.strptime(bd, '%d.%m.%Y').date()
                            except:
                                birth_date = datetime.strptime(bd, '%d.%m.%y').date()
                    elif isinstance(bd, pd.Timestamp):
                        birth_date = bd.date()
                    elif isinstance(bd, (int, float)):
                        from datetime import datetime as dt
                        birth_date = dt.fromordinal(dt(1900, 1, 1).toordinal() + int(bd) - 2).date()

                if not birth_date:
                    skipped += 1
                    errors.append(f'Строка {idx + 2}: Не удалось определить дату рождения')
                    continue

                # Обработка поля gender
                gender = 'M'
                if pd.notna(row['Пол']):
                    g = str(row['Пол']).upper().strip()
                    if g in ['Ж', 'F', 'ЖЕН', 'FEMALE', 'ЖЕНСКИЙ', 'ЖЕНЩИНА']:
                        gender = 'F'

                # Обработка веса
                weight = None
                weight_col = 'Вес' if 'Вес' in df.columns else None

                if weight_col and pd.notna(row[weight_col]):
                    weight_str = str(row[weight_col]).strip()
                    weight_str = re.sub(r'[^\d.,-]', '', weight_str)
                    weight_str = weight_str.replace(',', '.')

                    try:
                        numbers = re.findall(r'\d+\.?\d*', weight_str)
                        if numbers:
                            weight = float(numbers[0])
                        else:
                            weight = float(weight_str) if weight_str else None
                    except:
                        weight = None

                if not weight or weight <= 0:
                    skipped += 1
                    errors.append(f'Строка {idx + 2}: Не указан вес или некорректное значение')
                    continue

                # Обработка клуба
                club = 'ШКК РТ (Казань)'
                if 'Клуб' in df.columns and pd.notna(row['Клуб']):
                    club = str(row['Клуб']).strip()

                # Обработка тренера - ВАЖНО для распределения
                coach = ''
                if 'Тренер' in df.columns and pd.notna(row['Тренер']):
                    coach = str(row['Тренер']).strip()

                participant = Participant(
                    tournament=tournament,
                    last_name=str(row['Фамилия']).strip(),
                    first_name=str(row['Имя']).strip(),
                    birth_date=birth_date,
                    gender=gender,
                    weight=weight,
                    club=club,
                    coach=coach,
                    source_file=excel_file.name,
                    row_number=idx + 2
                )
                participant.save()
                imported += 1

            except Exception as e:
                errors.append(f'Строка {idx + 2}: {str(e)}')

        return {
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'errors': errors
        }

    except Exception as e:
        return {'success': False, 'error': f'Ошибка при чтении файла: {str(e)}'}