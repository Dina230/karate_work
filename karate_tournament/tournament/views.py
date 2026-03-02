from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Max
from django.http import JsonResponse, HttpResponse
from datetime import date
import pandas as pd

from .models import Tournament, Participant, Match
from .forms import ParticipantForm, MatchResultForm, ExcelUploadForm
from .utils import get_unique_categories, generate_bracket_for_category, get_category_stats, process_excel_file


def index(request):
    """Главная страница"""
    tournaments = Tournament.objects.filter(is_active=True)

    # Берем первый турнир для ссылок
    first_tournament = tournaments.first()

    # Статистика
    total_participants = Participant.objects.count()

    context = {
        'tournaments': tournaments,
        'first_tournament': first_tournament,
        'total_participants': total_participants,
    }
    return render(request, 'tournament/index.html', context)


def register_participant(request, tournament_id):
    """Регистрация нового участника"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    if request.method == 'POST':
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.tournament = tournament
            participant.save()  # При сохранении автоматически определятся категории

            messages.success(request,
                             f'Участник {participant.last_name} {participant.first_name} успешно зарегистрирован!')
            return redirect('participant_list', tournament_id=tournament.id)
    else:
        form = ParticipantForm()

    context = {
        'form': form,
        'tournament': tournament,
    }
    return render(request, 'tournament/register_participant.html', context)


def participant_list(request, tournament_id):
    """Список всех участников турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    participants = Participant.objects.filter(tournament=tournament)

    # Фильтры
    age_filter = request.GET.get('age')
    gender_filter = request.GET.get('gender')
    weight_filter = request.GET.get('weight')

    if age_filter:
        participants = participants.filter(age_category=age_filter)
    if gender_filter:
        participants = participants.filter(gender=gender_filter)
    if weight_filter:
        participants = participants.filter(weight_category=weight_filter)

    # Уникальные значения для фильтров
    age_categories = participants.values_list('age_category', flat=True).distinct().order_by('age_category')
    weight_categories = participants.values_list('weight_category', flat=True).distinct().order_by('weight_category')

    # Подсчет участников из Excel
    excel_count = participants.filter(source_file__isnull=False).count()
    manual_count = participants.filter(source_file__isnull=True).count()

    context = {
        'tournament': tournament,
        'participants': participants,
        'age_categories': age_categories,
        'weight_categories': weight_categories,
        'selected_age': age_filter,
        'selected_gender': gender_filter,
        'selected_weight': weight_filter,
        'excel_count': excel_count,
        'manual_count': manual_count,
    }
    return render(request, 'tournament/participant_list.html', context)


def category_list(request, tournament_id):
    """Список всех категорий с количеством участников"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    stats = get_category_stats(tournament)

    context = {
        'tournament': tournament,
        'stats': stats,
    }
    return render(request, 'tournament/category_list.html', context)


def generate_all_brackets(request, tournament_id):
    """Генерация турнирных сеток для всех категорий"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    if request.method == 'POST':
        categories = get_unique_categories(tournament)
        generated = 0
        skipped = 0

        for age_category, gender, weight_category in categories:
            success = generate_bracket_for_category(tournament, age_category, gender, weight_category)
            if success:
                generated += 1
            else:
                skipped += 1

        messages.success(request, f'Создано сеток: {generated}, пропущено (мало участников): {skipped}')
        return redirect('category_list', tournament_id=tournament.id)

    # Подсчет количества категорий с достаточным числом участников
    categories = get_unique_categories(tournament)
    ready_categories = 0
    stats = get_category_stats(tournament)

    # Считаем готовые категории
    for age_category, gender, weight_category in categories:
        count = Participant.objects.filter(
            tournament=tournament,
            age_category=age_category,
            gender=gender,
            weight_category=weight_category
        ).count()
        if count >= 2:
            ready_categories += 1

    context = {
        'tournament': tournament,
        'total_categories': len(categories),
        'ready_categories': ready_categories,
        'stats': stats,
    }
    return render(request, 'tournament/generate_all_brackets.html', context)


def generate_bracket_for_category_view(request, tournament_id, age_category, gender, weight_category):
    """Генерация сетки для конкретной категории"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Преобразуем пол из русского в английский
    gender_code = gender
    if gender == 'Ж':
        gender_code = 'F'
    elif gender == 'М':
        gender_code = 'M'

    if request.method == 'POST':
        success = generate_bracket_for_category(tournament, age_category, gender_code, weight_category)

        if success:
            messages.success(request, 'Турнирная сетка успешно создана!')
        else:
            messages.error(request, 'Не удалось создать сетку. Недостаточно участников (минимум 2).')

        return redirect('category_bracket',
                        tournament_id=tournament.id,
                        age_category=age_category,
                        gender=gender,
                        weight_category=weight_category)

    # Если GET запрос, просто показываем страницу категории
    return redirect('category_bracket',
                    tournament_id=tournament.id,
                    age_category=age_category,
                    gender=gender,
                    weight_category=weight_category)


def category_bracket(request, tournament_id, age_category, gender, weight_category):
    """Просмотр турнирной сетки для конкретной категории"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Преобразуем пол из русского в английский
    gender_code = gender
    if gender == 'Ж':
        gender_code = 'F'
    elif gender == 'М':
        gender_code = 'M'

    # Добавляем отладочный вывод в консоль
    print("=" * 50)
    print(f"ЗАПРОС КАТЕГОРИИ: {age_category}, {gender} -> {gender_code}, {weight_category}")
    print(f"Tournament ID: {tournament_id}")

    # Получаем участников категории (используем gender_code)
    participants = Participant.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender_code,
        weight_category=weight_category
    )

    print(f"Найдено участников в БД: {participants.count()}")
    for p in participants:
        print(f"  - {p.last_name} {p.first_name} (ID: {p.id}, вес: {p.weight})")

    # Получаем матчи (используем gender_code)
    matches = Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender_code,
        weight_category=weight_category
    ).order_by('round_number', 'match_order')

    print(f"Найдено матчей: {matches.count()}")

    # Группируем по раундам
    rounds = {}
    for match in matches:
        if match.round_number not in rounds:
            rounds[match.round_number] = []
        rounds[match.round_number].append(match)
        p1_name = match.participant1.last_name if match.participant1 else "TBD"
        p2_name = match.participant2.last_name if match.participant2 else "TBD"
        print(f"  Раунд {match.round_number}: {p1_name} vs {p2_name}")

    # Определяем пол для отображения
    gender_display = 'Мужчины' if gender_code == 'M' else 'Женщины'

    # Создаем список участников для отладки в шаблоне
    participants_list = []
    for p in participants:
        participants_list.append({
            'id': p.id,
            'last_name': p.last_name,
            'first_name': p.first_name,
            'club': p.club,
            'weight': p.weight
        })

    context = {
        'tournament': tournament,
        'age_category': age_category,
        'gender': gender_code,
        'gender_display': gender_display,
        'weight_category': weight_category,
        'rounds': sorted(rounds.items()),
        'participants': participants,
        'participants_count': participants.count(),
        'debug_participants': participants_list,
    }

    print(f"Передано в шаблон: participants_count={participants.count()}")
    print("=" * 50)

    return render(request, 'tournament/category_bracket.html', context)


def match_detail(request, match_id):
    """Детали матча и ввод результатов с обработкой боя за 3 место и неявок"""
    match = get_object_or_404(Match, id=match_id)

    if request.method == 'POST':
        form = MatchResultForm(request.POST, instance=match)
        if form.is_valid():
            # Сохраняем данные до обновления
            winner = form.cleaned_data.get('winner')
            status = form.cleaned_data.get('status')

            match = form.save()

            # Обработка завершенного матча или неявки
            if status in ['completed', 'walkover'] and winner:
                # Автоматически заполняем следующий матч
                if match.next_match:
                    if not match.next_match.participant1:
                        match.next_match.participant1 = winner
                        match.next_match.save()
                        print(f"Победитель {winner.last_name} добавлен в следующий матч (позиция 1)")
                    elif not match.next_match.participant2 and match.next_match.participant1 != winner:
                        match.next_match.participant2 = winner
                        match.next_match.save()
                        print(f"Победитель {winner.last_name} добавлен в следующий матч (позиция 2)")

                # Обработка боя за 3 место (полуфиналы)
                if match.round_name == "1/2" and hasattr(match, 'third_place_match') and match.third_place_match:
                    # Определяем проигравшего
                    if winner == match.participant1:
                        loser = match.participant2
                    else:
                        loser = match.participant1

                    if loser:
                        third = match.third_place_match
                        if not third.participant1:
                            third.participant1 = loser
                            third.save()
                            messages.info(request,
                                          f'{loser.last_name} {loser.first_name} будет участвовать в бое за 3 место')
                        elif not third.participant2 and third.participant1 != loser:
                            third.participant2 = loser
                            third.save()
                            messages.info(request,
                                          f'{loser.last_name} {loser.first_name} будет участвовать в бое за 3 место')

                if status == 'completed':
                    messages.success(request,
                                     f'Результат сохранен! Победитель: {winner.last_name} {winner.first_name}')
                else:  # walkover
                    messages.info(request,
                                  f'Зафиксирована неявка. Победитель: {winner.last_name} {winner.first_name} проходит дальше')

            elif status == 'walkover' and not winner:
                messages.error(request, 'При неявке необходимо выбрать победителя!')
                return redirect('match_detail', match_id=match.id)

            return redirect('category_bracket',
                            tournament_id=match.tournament.id,
                            age_category=match.age_category,
                            gender=('М' if match.gender == 'M' else 'Ж'),
                            weight_category=match.weight_category)
    else:
        form = MatchResultForm(instance=match)

    context = {
        'match': match,
        'form': form,
    }
    return render(request, 'tournament/match_detail.html', context)


def tournament_stats(request, tournament_id):
    """Статистика по турниру"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    participants = Participant.objects.filter(tournament=tournament)
    matches = Match.objects.filter(tournament=tournament)

    # Общая статистика
    stats = {
        'total_participants': participants.count(),
        'male': participants.filter(gender='M').count(),
        'female': participants.filter(gender='F').count(),
        'total_matches': matches.count(),
        'completed_matches': matches.filter(status='completed').count(),
        'scheduled_matches': matches.filter(status='scheduled').count(),
        'in_progress_matches': matches.filter(status='in_progress').count(),
        'walkover_matches': matches.filter(status='walkover').count(),
    }

    # Распределение по возрастам
    age_distribution = {}
    for p in participants:
        age_distribution[p.age_category] = age_distribution.get(p.age_category, 0) + 1

    # Распределение по весовым категориям
    weight_distribution = {}
    for p in participants:
        key = f"{p.age_category} - {p.weight_category}"
        weight_distribution[key] = weight_distribution.get(key, 0) + 1

    # Статистика по клубам
    club_stats = {}
    for p in participants:
        club_stats[p.club] = club_stats.get(p.club, 0) + 1

    # Топ-5 клубов
    top_clubs = sorted(club_stats.items(), key=lambda x: x[1], reverse=True)[:5]

    # Статистика по источникам
    excel_participants = participants.filter(source_file__isnull=False).count()
    manual_participants = participants.filter(source_file__isnull=True).count()

    context = {
        'tournament': tournament,
        'stats': stats,
        'age_distribution': sorted(age_distribution.items()),
        'weight_distribution': sorted(weight_distribution.items()),
        'top_clubs': top_clubs,
        'total_clubs': len(club_stats),
        'excel_participants': excel_participants,
        'manual_participants': manual_participants,
    }
    return render(request, 'tournament/tournament_stats.html', context)


def upload_excel(request, tournament_id):
    """Загрузка участников из Excel файла"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            clear_existing = form.cleaned_data['clear_existing']

            # Обрабатываем файл
            result = process_excel_file(excel_file, tournament, clear_existing)

            if result['success']:
                messages.success(
                    request,
                    f'Успешно импортировано участников: {result["imported"]}'
                )
                if result['errors']:
                    for error in result['errors'][:5]:  # Показываем первые 5 ошибок
                        messages.warning(request, error)
                    if len(result['errors']) > 5:
                        messages.warning(request, f'И еще {len(result["errors"]) - 5} ошибок')
            else:
                messages.error(request, result['error'])

            return redirect('participant_list', tournament_id=tournament.id)
    else:
        form = ExcelUploadForm()

    # Получаем пример структуры
    example_data = [
        ['Иванов', 'Иван', '15.05.2010', 'М', 45.5, 'Клуб "Восток"', 'Петров А.И.'],
        ['Петрова', 'Анна', '20.08.2011', 'Ж', 38.0, 'Клуб "Самурай"', 'Сидоров В.П.'],
        ['Сидоров', 'Петр', '10.03.2009', 'М', 52.0, 'ДЮСШ №1', 'Иванов С.Н.'],
    ]

    context = {
        'tournament': tournament,
        'form': form,
        'example_data': example_data,
    }
    return render(request, 'tournament/upload_excel.html', context)


def download_template(request, tournament_id):
    """Скачать шаблон Excel файла"""
    # Создаем пример данных
    data = {
        'Фамилия': ['Иванов', 'Петров', 'Сидорова'],
        'Имя': ['Иван', 'Петр', 'Анна'],
        'Дата рождения': ['15.05.2010', '20.08.2009', '10.03.2011'],
        'Пол': ['М', 'М', 'Ж'],
        'Вес': [45.5, 52.0, 38.5],
        'Клуб': ['Клуб "Восток"', 'Клуб "Самурай"', 'ДЮСШ №1'],
        'Тренер': ['Петров А.И.', 'Сидоров В.П.', 'Иванова Е.Н.']
    }

    df = pd.DataFrame(data)

    # Создаем HTTP ответ с Excel файлом
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="template_participants.xlsx"'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Участники')

    return response


def delete_participant(request, participant_id):
    """Удаление участника"""
    participant = get_object_or_404(Participant, id=participant_id)
    tournament_id = participant.tournament.id
    name = f"{participant.last_name} {participant.first_name}"

    if request.method == 'POST':
        participant.delete()
        messages.success(request, f'Участник {name} удален')
        return redirect('participant_list', tournament_id=tournament_id)

    context = {
        'participant': participant,
    }
    return render(request, 'tournament/delete_participant.html', context)


def edit_participant(request, participant_id):
    """Редактирование данных участника"""
    participant = get_object_or_404(Participant, id=participant_id)

    if request.method == 'POST':
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            form.save()
            messages.success(request, f'Данные участника обновлены')
            return redirect('participant_list', tournament_id=participant.tournament.id)
    else:
        form = ParticipantForm(instance=participant)

    context = {
        'form': form,
        'participant': participant,
    }
    return render(request, 'tournament/edit_participant.html', context)


def clear_category_matches(request, tournament_id, age_category, gender, weight_category):
    """Очистка всех матчей в категории"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Преобразуем пол из русского в английский
    gender_code = gender
    if gender == 'Ж':
        gender_code = 'F'
    elif gender == 'М':
        gender_code = 'M'

    if request.method == 'POST':
        Match.objects.filter(
            tournament=tournament,
            age_category=age_category,
            gender=gender_code,
            weight_category=weight_category
        ).delete()

        messages.success(request, f'Все матчи в категории удалены')
        return redirect('category_list', tournament_id=tournament.id)

    gender_display = 'Мужчины' if gender_code == 'M' else 'Женщины'
    context = {
        'tournament': tournament,
        'age_category': age_category,
        'gender': gender,
        'gender_display': gender_display,
        'weight_category': weight_category,
    }
    return render(request, 'tournament/clear_category.html', context)


def search_participants(request, tournament_id):
    """Поиск участников"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    query = request.GET.get('q', '')

    if query:
        participants = Participant.objects.filter(
            tournament=tournament
        ).filter(
            Q(last_name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(club__icontains=query)
        )
    else:
        participants = Participant.objects.none()

    context = {
        'tournament': tournament,
        'participants': participants,
        'query': query,
    }
    return render(request, 'tournament/search_results.html', context)


def print_bracket(request, tournament_id, age_category, gender, weight_category):
    """Версия турнирной сетки для печати"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Преобразуем пол из русского в английский
    gender_code = gender
    if gender == 'Ж':
        gender_code = 'F'
    elif gender == 'М':
        gender_code = 'M'

    matches = Match.objects.filter(
        tournament=tournament,
        age_category=age_category,
        gender=gender_code,
        weight_category=weight_category
    ).order_by('round_number', 'match_order')

    rounds = {}
    for match in matches:
        if match.round_number not in rounds:
            rounds[match.round_number] = []
        rounds[match.round_number].append(match)

    gender_display = 'Мужчины' if gender_code == 'M' else 'Женщины'

    context = {
        'tournament': tournament,
        'age_category': age_category,
        'gender_display': gender_display,
        'weight_category': weight_category,
        'rounds': sorted(rounds.items()),
        'print_mode': True,
    }
    return render(request, 'tournament/print_bracket.html', context)


def ajax_get_participants(request, tournament_id):
    """API для получения списка участников (для AJAX запросов)"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    category = request.GET.get('category', '')

    if category:
        # Ожидаем формат: "age_category|gender|weight_category"
        parts = category.split('|')
        if len(parts) == 3:
            age, gen, weight = parts
            # Преобразуем пол если нужно
            if gen == 'Ж':
                gen = 'F'
            elif gen == 'М':
                gen = 'M'
            participants = Participant.objects.filter(
                tournament=tournament,
                age_category=age,
                gender=gen,
                weight_category=weight
            ).values('id', 'last_name', 'first_name', 'club')
        else:
            participants = []
    else:
        participants = Participant.objects.filter(
            tournament=tournament
        ).values('id', 'last_name', 'first_name', 'club', 'age_category', 'weight_category')

    return JsonResponse(list(participants), safe=False)