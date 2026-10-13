"""Build and run plain SQL that fills the database with demo items.

Run: uv run python common/data/seed_demo.py
"""

import json
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vas3k_base.settings")

import django

django.setup()

from django.db import connection  # noqa: E402
from django.utils import timezone  # noqa: E402

from categories.models import Category  # noqa: E402

USERS = [
    ("anna-kovaleva", "Анна Ковалёва", "Берлин", "Германия", "Продакт. Собираю врачей, кафе и нормальные сервисы."),
    ("mark-shevchenko", "Марк Шевченко", "Мюнхен", "Германия", "Инженер. Часто ищу мастеров и скидки на технику."),
    ("lena-petrova", "Елена Петрова", "Гамбург", "Германия", "Переехала год назад. Делюсь тем, что уже проверила."),
    ("nikola-jovic", "Никола Йович", "Белград", "Сербия", "Дизайнер. Знаю, где в Белграде не разводят."),
    ("milica-stojanovic", "Милица Стоянович", "Нови-Сад", "Сербия", "Учу сербский и хожу на все встречи, до которых доеду."),
    ("stefan-nikolic", "Стефан Николич", "Ниш", "Сербия", "Делаю сайты. Иногда продаю лишнее и зову на настолки."),
    ("nino-beridze", "Нино Беридзе", "Тбилиси", "Грузия", "Живу в Вере. Могу подсказать врача, вино и квартиру."),
    ("giorgi-kalandze", "Гиорги Каландадзе", "Батуми", "Грузия", "Снимаю жильё посуточно и чиню всё, что ломается."),
    ("tamara-gelashvili", "Тамара Гелашвили", "Кутаиси", "Грузия", "Преподаю английский. Вечерами зову на прогулки."),
    ("oleg-smirnov", "Олег Смирнов", "Удалённо", "Мир", "Работаю из разных стран. Пишу про удалёнку и подписки."),
    ("kate-orlova", "Катя Орлова", "Германия", "Германия", "Езжу между Берлином и Мюнхеном. Скидки и попутчики."),
    ("irakli-mchedlidze", "Иракли Мчедлидзе", "Грузия", "Грузия", "Вожу людей по стране и знаю, кому звонить в дороге."),
]

# subcategory, category, kind, four titles
# kind: place, coupon, job, market, social, online
CATALOG = [
    ("doctors", "recommendations", "place", [
        "Терапевт, который не гонит по десяти специалистам",
        "Семейный врач с нормальной записью, не конвейер",
        "ЛОР, говорит спокойно и объясняет, что пить",
        "Педиатр для тех, кто только переехал и ещё без страховки",
    ]),
    ("dentists", "recommendations", "place", [
        "Стоматолог, который не разводит на коронки с порога",
        "Чистка и лечение без сюрприза в счёте",
        "Детский стоматолог, ребёнок не орёт",
        "Срочно приняли с флюсом в тот же день",
    ]),
    ("psychologists", "recommendations", "place", [
        "Психолог на русском, без эзотерики",
        "Терапия для релокантов: тревога, сон, «я тут чужой»",
        "Парные сессии, можно онлайн и очно",
        "Психолог, который не обещает починить жизнь за три встречи",
    ]),
    ("lawyers", "recommendations", "place", [
        "Адвокат по ВНЖ, отвечает прямо, а не «посмотрим»",
        "Помогли с договором аренды до подписания",
        "Юрист по регистрации фирмы для фрилансера",
        "Консультация по штрафам и письмам из ведомств",
    ]),
    ("accountants", "recommendations", "place", [
        "Бухгалтер для мини-ГмбХ и фриланса",
        "Сдала годовую декларацию и объяснила, что куда",
        "Бухгалтер, который сам напоминает про сроки",
        "Разложили налоги по полочкам за одну встречу",
    ]),
    ("movers", "recommendations", "place", [
        "Грузчики, которые не пропали в день переезда",
        "Переезд двушки за полдня, мебель не поцарапали",
        "Машина с гидробортом, занесли пианино",
        "Двое ребят на пару часов, без минималки на весь день",
    ]),
    ("plumbers", "recommendations", "place", [
        "Сантехник приехал в тот же вечер",
        "Поменял смеситель и не оставил потоп у соседей",
        "Прочистили стояк, пахнет нормально",
        "Мастер, который называет цену до того, как разобрать стену",
    ]),
    ("electricians", "recommendations", "place", [
        "Электрик собрал щиток и подписал автоматы",
        "Повесили люстру и починили розетку на кухне",
        "Провели свет на балконе без «а давайте ещё щиток»",
        "Приехал с своим инструментом, ушёл через час",
    ]),
    ("mechanics", "recommendations", "place", [
        "Автомеханик, который показывает старую деталь",
        "Заменили колодки и не накрутили диагностику",
        "Сервис, где говорят по-русски и пишут смету",
        "Перезимовали на их резине, развал сделали честно",
    ]),
    ("repair", "recommendations", "place", [
        "Починили макбук после кофе, данные на месте",
        "Замена экрана телефона за день",
        "Стиралка снова отжимает, мастер был свой",
        "Починили ноутбук, который «официалы» списали",
    ]),
    ("tutors", "recommendations", "place", [
        "Репетитор по немецкому, говорим с первого урока",
        "Математика школьнику, без крика и зубрёжки",
        "Сербский для жизни: магазин, врач, аренда",
        "Английский для собесов, не учебник из школы",
    ]),
    ("photo", "recommendations", "place", [
        "Фотограф на документы, которые реально принимают",
        "Семейная съёмка в парке, дети не замучены",
        "Предметные картинки для объявлений, за вечер",
        "Видео с дня рождения, смонтировали за три дня",
    ]),
    ("services-beauty", "recommendations", "place", [
        "Парикмахер, который слушает, а не «вам так лучше»",
        "Маникюр без запаха на весь подъезд",
        "Барбер, запись в тот же день после работы",
        "Брови и ничего лишнего, вышла как человек",
    ]),
    ("cleaning", "recommendations", "place", [
        "Уборка после съёма, квартира снова белая",
        "Регулярная уборка раз в две недели, свои ключи",
        "Помыли окна на четвёртом этаже",
        "Клининг перед сдачей жилья хозяину",
    ]),
    ("translation", "recommendations", "place", [
        "Присяжный перевод свидетельств, приняли с первого раза",
        "Переводчик на приём к врачу",
        "Перевели договор аренды нормальным языком",
        "Нотариальный перевод диплома за два дня",
    ]),
    ("food", "coupons", "coupon", [
        "Ужин на двоих, минус десерт по коду",
        "Обед в грузинском дворике дешевле, чем с улицы",
        "Завтрак до 12, кофе второй в подарок",
        "Сет на компанию, скидка если сказать, что из Клуба",
    ]),
    ("groceries", "coupons", "coupon", [
        "Доставка продуктов, первый заказ дешевле",
        "Рынок по субботам, своим отвешивают честнее",
        "Промо на привычный супермаркет у дома",
        "Фермерская корзина раз в неделю",
    ]),
    ("clothes", "coupons", "coupon", [
        "Сезонная распродажа, код снимает ещё десять процентов",
        "Обувь, которую можно сдать, если не сели",
        "Базовый гардероб без «коллекции», просто скидка",
        "Детская одежда, на второй вещи цена ниже",
    ]),
    ("electronics", "coupons", "coupon", [
        "Наушники со скидкой для своих",
        "Код на магазин техники, проверила на зарядке",
        "Монитор дешевле, чем на витрине",
        "Мелкая техника для кухни, код в корзине",
    ]),
    ("travel", "coupons", "coupon", [
        "Поезд по стране дешевле, если брать нашим кодом",
        "Хостел для своих, завтрак включён",
        "Скидка на багаж, когда летите налегке и всё равно сдаёте",
        "Аренда машины на выходные, каско уже внутри",
    ]),
    ("beauty", "coupons", "coupon", [
        "Чистка лица, первым визитом дешевле",
        "Массаж после переезда, шея отдельно благодарит",
        "Аптечная косметика по коду, не серая",
        "Стрижка + уход, второе почти даром",
    ]),
    ("sport", "coupons", "coupon", [
        "Месяц зала без годового контракта",
        "Йога для начинающих, коврик дают",
        "Бассейн утром, абонемент дешевле через код",
        "Скалодром, первый визит почти бесплатный",
    ]),
    ("education", "coupons", "coupon", [
        "Курс языка, модуль дешевле для участников Клуба",
        "Вечерние курсы по местным налогам, коротко и по делу",
        "Скидка на онлайн-школу для ребёнка",
        "Интенсив перед экзаменом, группа маленькая",
    ]),
    ("fun", "coupons", "coupon", [
        "Билеты в кино в будний вечер дешевле",
        "Квест на компанию, шестому бесплатно",
        "Концерт в маленьком зале, код на кассе",
        "Выставка, вход дешевле если показать объявление",
    ]),
    ("home", "coupons", "coupon", [
        "Скидка в строительном, когда чините первое жильё",
        "Шторы на заказ, замер бесплатный",
        "Посуда и мелочи для пустой квартиры",
        "Краска и кисти, код на кассе у входа",
    ]),
    ("auto", "coupons", "coupon", [
        "Мойка без очереди в обед, дешевле по коду",
        "Шиномонтаж, второе колесо со скидкой",
        "Детское кресло в прокат на месяц",
        "Топливная карта, кешбэк копеечный, но честный",
    ]),
    ("internet", "coupons", "coupon", [
        "Домашний интернет без годового замка",
        "Симка с нормальным интернетом, не туристическая",
        "Роутер в подарок, если подключиться нашим кодом",
        "Мобильная связь, пока ещё не оформили местный контракт",
    ]),
    ("subscriptions", "coupons", "online", [
        "Семейная подписка на музыку, ищу четвёртого",
        "Общий аккаунт на кино, слот свободен",
        "Облако для картинок, годовой план дешевле",
        "Подписка на новости и журналы, код ещё живой",
    ]),
    ("other", "coupons", "coupon", [
        "Скидка, которая не влезла ни в одну полку",
        "Промокод на цветы, если внезапно нужно",
        "Химчистка пальто, дешевле в будни",
        "Код на доставку чего угодно в пределах города",
    ]),
    ("it", "jobs", "job", [
        "Бэкенд в маленький продукт, офис два дня в неделю",
        "Фронтенд, ревью живое, не тикет-кладбище",
        "Девопс на партизанку, потом можно в штат",
        "Данные и аналитика, команда говорит по-русски на кухне",
    ]),
    ("design", "jobs", "job", [
        "Продуктовый дизайнер, портфолио важнее диплома",
        "Бренд и презентации для студии из четырёх человек",
        "Ищем дизайнера в интерфейсы, можно часть недели дома",
        "Графика для маркетплейса, задачи понятные",
    ]),
    ("marketing", "jobs", "job", [
        "Маркетолог, который сам пишет, а не только брифует",
        "Перформанс, бюджет небольшой, отчёт раз в неделю",
        "Контент и соцсети локального сервиса",
        "CRM и письма, база уже есть, руки нужны",
    ]),
    ("sales", "jobs", "job", [
        "Продажи в B2B, цикл длинный, процент белый",
        "Аккаунт для своих клиентов на русском и местном",
        "Менеджер зала в маленьком шоуруме",
        "Партнёрки, без холодных звонков с восьми утра",
    ]),
    ("management", "jobs", "job", [
        "Проджект на два продукта, команда уже собрана",
        "Операционка кафе, нужен человек, а не герой",
        "Руководитель поддержки, смена дневная",
        "Координатор переездов, много чатов, мало политики",
    ]),
    ("finance", "jobs", "job", [
        "Бухгалтер в штат, не аутсорс",
        "Финансовый аналитик, таблицы и один совет директоров",
        "Казначей на полставки для маленькой фирмы",
        "Зарплатный бухгалтер, месяц закрываем без героизма",
    ]),
    ("jobs-education", "jobs", "job", [
        "Преподаватель языка взрослым, вечерами",
        "Вожатый на городской лагерь, смена короткая",
        "Куратор онлайн-группы, проверка домашек",
        "Учитель математики, группа до восьми человек",
    ]),
    ("medicine", "jobs", "job", [
        "Медсестра в частную практику, график человеческий",
        "Администратор клиники, русский и местный",
        "Ассистент стоматолога, обучат на месте",
        "Координатор пациентов, без ночных смен",
    ]),
    ("legal", "jobs", "job", [
        "Юрист в маленькую практику, ВНЖ и договоры",
        "Помощник адвоката, много бумаг, мало суда",
        "Комплаенс на удалёнке три дня в неделю",
        "Юрист по аренде, поток понятный",
    ]),
    ("production", "jobs", "job", [
        "Мастер смены на небольшое производство",
        "Сборщик мебели в цех, инструмент свой плюс",
        "Технолог еды, кухня уже запущена",
        "Контроль качества, глаза и таблицы",
    ]),
    ("logistics", "jobs", "job", [
        "Логист последней мили, город знает",
        "Кладовщик, смена дневная, без ночи",
        "Диспетчер машин, русский в рации нормально",
        "Закупки для маленького магазина",
    ]),
    ("admin", "jobs", "job", [
        "Офис-менеджер, гости, почта, канцелярия",
        "Ассистент основателя, календарь и поездки",
        "Администратор коворкинга на ресепшене",
        "Секретарь в практике, телефоны и запись",
    ]),
    ("internships", "jobs", "job", [
        "Стажировка в продукт, платят, не «за опыт»",
        "Летняя практика в дизайне, три месяца",
        "Стажёр в поддержку, скрипты уже написаны",
        "Практика у бухгалтера, можно после пар",
    ]),
    ("remote", "jobs", "online", [
        "Удалёнка, поддержка на русском, смены перекрывают Европу",
        "Редактор в распределённую команду, дедлайны дневные",
        "Разработчик, созвоны два раза в неделю, остальное тишина",
        "Операционист на удалёнке, задачи в трекере",
    ]),
    ("relocation", "jobs", "job", [
        "Вакансия с помощью в переезде, жильё на первый месяц",
        "Ищут человека, который уже в стране, бумаги готовы",
        "Релокация под ключ, если пройдёте собесы",
        "Офис ждёт тех, кто переехал в этом году",
    ]),
    ("freelance", "services", "place", [
        "Соберу лендинг за неделю, без агентской наценки",
        "Монтаж роликов для объявлений и соцсетей",
        "Настрою рекламу маленькому кафе",
        "Переведу сайт на местный язык, не машинкой",
    ]),
    ("tools", "services", "place", [
        "Дрель и стремянка на выходные",
        "Мойка высокого давления, заберу сам",
        "Проектор на вечер, экран в комплекте",
        "Перфоратор на день, залог наличными",
    ]),
    ("trips", "services", "social", [
        "Еду в соседний город в субботу, есть два места",
        "Ищу попутчика на море, бензин пополам",
        "Выезд в горы на день, места в машине есть",
        "Ночной поезд, купе, ищу спокойного соседа",
    ]),
    ("phones", "market", "market", [
        "Телефон после апгрейда, батарея ещё живая",
        "Наушники, коробка и чек на месте",
        "Зарядки и кабели пачкой, всё рабочее",
        "Планшет ребёнку уже мал, ваш может пригодиться",
    ]),
    ("computers", "market", "market", [
        "Ноутбук для учёбы, не для игр",
        "Монитор 27 дюймов, забирать из офиса",
        "Клавиатура и мышь, почти новые",
        "Системник, отдам с монитором если заберёте оба",
    ]),
    ("market-clothes", "market", "market", [
        "Пальто, размер промах, бирка на месте",
        "Обувь, носили два раза, не моя колодка",
        "Детские куртки, выросли за сезон",
        "Рубашки пачкой, офис больше не ношу",
    ]),
    ("furniture", "market", "market", [
        "Диван, самовывоз, помогу спустить",
        "Стол и два стула, кухня стала меньше",
        "Стеллаж, в разобранном виде влезет в легковую",
        "Кровать с матрасом, переезжаем и не везём с собой",
    ]),
    ("kids", "market", "market", [
        "Коляска, складная, ездили одно лето",
        "Стул для кормления, ребёнок уже за общим столом",
        "Игрушки пакетом, без мелких деталей",
        "Велосипед с дополнительными колёсами",
    ]),
    ("bikes", "market", "market", [
        "Городской велосипед, обслужен в этом месяце",
        "Детский велик, выросли",
        "Самокат взрослый, складывается",
        "Велокресло на багажник, одно лето",
    ]),
    ("market-auto", "market", "market", [
        "Зимняя резина, остаток сезона честный",
        "Детское кресло, группа следующая уже куплена",
        "Багажник на крышу, крепления под обычные рейлинги",
        "Набор инструмента из багажника, машину продал",
    ]),
    ("market-sport", "market", "market", [
        "Коврик и блоки для йоги",
        "Гантели, забирать с этажа, лифта нет",
        "Беговые кроссовки, размер не мой",
        "Палатка двухместная, ставили три раза",
    ]),
    ("books", "market", "market", [
        "Полка русской прозы, отдам пачкой дешевле",
        "Учебники языка с пометками, которые даже полезны",
        "Детские книги, уже перечитали сто раз",
        "Книги по работе, бумажные, не возвращать",
    ]),
    ("housing", "market", "place", [
        "Сдаём комнату в двушке, соседи тихие",
        "Квартира на два месяца, пока сами в отъезде",
        "Ищем соседа в трёшку, комната с дверью",
        "Студия у метро, заезд со следующей недели",
    ]),
    ("rent", "market", "place", [
        "Аренда места в кабинете на пару дней в неделю",
        "Мастерская по часам, стол и свет есть",
        "Кладовка в подвале, сухо",
        "Машина на день, когда своя в сервисе",
    ]),
    ("pets", "market", "place", [
        "Отдаём кота в добрые руки, привит",
        "Переноска и миски, пёс уже большой",
        "Ищем передержку на неделю",
        "Аквариум с тумбой, рыбок заберите тоже",
    ]),
    ("plants", "market", "market", [
        "Монстера выросла из угла, ищу новый дом",
        "Рассада помидоров с балкона",
        "Кашпо пачкой, переезд",
        "Фикус, огромный, самовывоз вдвоём",
    ]),
    ("hobby", "market", "market", [
        "Настолки, которые надоели своей компании",
        "Мольберт и краски, бросил кружок",
        "Гитара, струны новые, чехол в комплекте",
        "Набор для керамики, печи у меня нет",
    ]),
    ("free", "market", "market", [
        "Отдам даром коробки для переезда",
        "Стулья, четыре штуки, лишь бы забрали",
        "Детский стол, царапины честные",
        "Книги у подъезда не оставляю, напишите и подъеду",
    ]),
    ("meetups", "social", "social", [
        "Воскресный кофе, стол уже занял",
        "Знакомство для тех, кто в городе меньше полугода",
        "Завтрак перед работой, без презентаций",
        "Вечер «просто посидеть», тема свободная",
    ]),
    ("social-sport", "social", "social", [
        "Футбол по четвергам, уровень «не стыдно»",
        "Утренняя пробежка в парке, темп разговорный",
        "Волейбол в зале, мяч есть",
        "Велопрогулка на 30 километров, не гонка",
    ]),
    ("boardgames", "social", "social", [
        "Настолки в воскресенье, объясним правила",
        "Ищем четвёртого в кампанию, уже три встречи",
        "Лёгкие игры, можно с нуля",
        "Клуб в кафе, бронь на моё имя",
    ]),
    ("cinema", "social", "social", [
        "Кино в оригинале, потом разбор в баре рядом",
        "Детский сеанс, ищем ещё одну семью",
        "Ночной показ, билеты ещё есть",
        "Смотрим дома, экран большой, попкорн ваш",
    ]),
    ("music", "social", "social", [
        "Живая музыка в баре, столик на шестерых",
        "Квартирник, акустика, соседи предупреждены",
        "Ищу людей на хор, слух желателен, не обязателен",
        "Джем для тех, кто играет посредственно, как я",
    ]),
    ("social-travel", "social", "social", [
        "Выходные в соседнем городе, жильё уже есть",
        "Однодневный выезд, билеты покупаем вместе",
        "Ищу компанию на праздники, одному скучно",
        "Поход без палаток, ночёвка в домике",
    ]),
    ("languages", "social", "online", [
        "Языковой обмен: русский на местный, час на час",
        "Разговорный клуб по средам, ошибки не считаем",
        "Парная практика перед экзаменом",
        "Переписка и один созвон в неделю",
    ]),
    ("volunteering", "social", "social", [
        "Помочь с раздачей еды в субботу утром",
        "Нужны руки на ярмарку, смена четыре часа",
        "Репетиторство детям при центре, раз в неделю",
        "Переезд приюта, нужны машины и люди",
    ]),
    ("romance", "social", "social", [
        "Ищу, с кем ходить на выставки, без анкет",
        "Ужин вдвоём, если оба не любите смолток про работу",
        "Прогулка у реки, дальше как пойдёт",
        "Кофе и честный разговор, не приложение",
    ]),
    ("parents", "social", "social", [
        "Площадка по утрам, пока детский сад на каникулах",
        "Ищем семью с ребёнком того же возраста",
        "Воскресный кружок, родители сидят тут же",
        "Колясочная прогулка, темп медленный",
    ]),
    ("gaming", "social", "online", [
        "Ищем пятого в вечерний рейд, микрофон обязателен",
        "Настольный варгейм раз в две недели",
        "Спокойный кооператив по выходным",
        "Турнир в районе, уровень любительский",
    ]),
    ("bars", "social", "social", [
        "Бар, где не орёт музыка и можно говорить",
        "Дегустация вина, веду её я, платите только вино",
        "Завтрак в заведении, где не смотрят косо на ноутбук",
        "Пиво после работы, стол на углу",
    ]),
    ("networking", "social", "online", [
        "Завтрак предпринимателей, без питчей на десять минут",
        "Созвон тех, кто делает маленькие продукты",
        "Обмен контактами бухгалтеров и юристов, по делу",
        "Встреча фрилансеров, каждый рассказывает одну задачу",
    ]),
    ("social-pets", "social", "social", [
        "Собачья прогулка в парке по субботам",
        "Ищу компанию для передержки опыта, не клиника",
        "Котики на подоконнике, приходите знакомиться",
        "Дрессировка на площадке, тренер свой, места есть",
    ]),
]

CLOSINGS = {
    "place": [
        "Хожу сам уже полгода, счёт совпал с тем, что назвали заранее.",
        "Можно писать вечером, отвечают на следующий день, не теряются.",
        "Если нужно, скину, как добраться от остановки.",
        "Записывайтесь заранее: в удачный день окон нет.",
    ],
    "coupon": [
        "Код назвали на кассе, скидку увидели в чеке.",
        "Работает и на вынос, и если сидеть внутри.",
        "Не суммируется с другими акциями, я проверял.",
        "Если код уже погас, напишите, обновлю объявление.",
    ],
    "job": [
        "Напишите коротко, кто вы и когда можете выйти. Портфолио ссылкой.",
        "Вилка в первом ответе, без «зависит от вас» три недели.",
        "Испытательный есть, но его обсуждают до оффера.",
        "Можно без местного диплома, если уже живёте здесь.",
    ],
    "market": [
        "Самовывоз, торг уместен, если забираете сегодня.",
        "Картинки по запросу, в объявлении то, что есть сейчас.",
        "Держу до выходных, потом отдам дальше по очереди.",
        "Оплата наличными или переводом при встрече.",
    ],
    "social": [
        "Напишите, если идёте, чтобы я понимал, сколько нас.",
        "Опоздания нормальны, начало мягкое.",
        "Можно одного друга, предупредите.",
        "Если место поменяется, напишу всем, кто отметился.",
    ],
    "online": [
        "Город не важен, созвон в удобный вечер.",
        "Всё в переписке, звонок только если сами хотите.",
        "Часовой пояс Европа, утром отвечаю медленнее.",
        "Ссылку и детали пришлю после короткого сообщения.",
    ],
}

ADDRESSES = {
    "berlin": "Kreuzberg, Oranienstraße {n}, Berlin",
    "munich": "Schwabing, Leopoldstraße {n}, München",
    "hamburg": "Sternschanze, Schanzenstraße {n}, Hamburg",
    "belgrade": "Vračar, Kralja Milana {n}, Beograd",
    "novi-sad": "Stari Grad, Zmaj Jovina {n}, Novi Sad",
    "nis": "Centar, Obrenovićeva {n}, Niš",
    "tbilisi": "Вера, Барнови {n}, Тбилиси",
    "batumi": "Центр, Мемеда Абашидзе {n}, Батуми",
    "kutaisi": "Центр, Руставели {n}, Кутаиси",
}

MAPS = {
    "berlin": "https://maps.google.com/?q=Oranienstra%C3%9Fe+Berlin",
    "munich": "https://maps.google.com/?q=Leopoldstra%C3%9Fe+M%C3%BCnchen",
    "hamburg": "https://maps.google.com/?q=Schanzenstra%C3%9Fe+Hamburg",
    "belgrade": "https://maps.google.com/?q=Kralja+Milana+Belgrade",
    "novi-sad": "https://maps.google.com/?q=Zmaj+Jovina+Novi+Sad",
    "nis": "https://maps.google.com/?q=Obrenoviceva+Nis",
    "tbilisi": "https://maps.google.com/?q=Barnovi+Tbilisi",
    "batumi": "https://maps.google.com/?q=Memed+Abashidze+Batumi",
    "kutaisi": "https://maps.google.com/?q=Rustaveli+Kutaisi",
}

PHONES = {
    "berlin": "+49 30 120{n:04d}",
    "munich": "+49 89 210{n:04d}",
    "hamburg": "+49 40 330{n:04d}",
    "belgrade": "+381 11 40{n:05d}",
    "novi-sad": "+381 21 48{n:04d}",
    "nis": "+381 18 50{n:04d}",
    "tbilisi": "+995 32 2{n:06d}",
    "batumi": "+995 422 2{n:05d}",
    "kutaisi": "+995 431 2{n:05d}",
    "de": "+49 171 200{n:04d}",
    "rs": "+381 60 300{n:04d}",
    "ge": "+995 555 10{n:04d}",
    None: "+49 151 700{n:04d}",
}

CITIES = [
    ("de", "berlin"),
    ("de", "munich"),
    ("de", "hamburg"),
    ("rs", "belgrade"),
    ("rs", "novi-sad"),
    ("rs", "nis"),
    ("ge", "tbilisi"),
    ("ge", "batumi"),
    ("ge", "kutaisi"),
]

COUNTRIES = ["de", "rs", "ge"]

COMMENTS = [
    "Ходил на прошлой неделе, всё как написано. Спасибо.",
    "А по цене сейчас не выросло? Хочу понять, прежде чем ехать.",
    "Можно с детьми или лучше без?",
    "Записался. Если что-то изменится, допишу сюда.",
    "Были вдвоём, остались довольны и вернёмся.",
    "Не дозвонился, в телеграме ответили через час.",
    "Адрес верный, вход со двора, звонок справа.",
    "Промокод сработал, скидку видно в чеке.",
    "Ищу такое же, но вечером. Есть окно?",
    "Год назад было слабее. Сейчас заметно лучше.",
    "Подскажите, на месте говорят по-русски?",
    "Забрал вчера, всё на месте. Могу рекомендовать.",
]

REPLIES = [
    "Да, по-русски говорят, я сам так ходил.",
    "Цена та же, был вчера.",
    "С детьми пустили без вопросов.",
    "Вход со двора, я тоже сначала промахнулся.",
    "Код у меня тоже прошёл.",
    "Вечером лучше написать заранее, днём могут быть заняты.",
    "Если не ответят, напишите ещё раз, иногда тонут в чатах.",
    "Спасибо, что проверили, я как раз собирался.",
    "В субботу очереди почти не было.",
    "Могу скинуть, как дойти от метро.",
]


def sql_quote(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return "'" + str(value).replace("'", "''") + "'"


def contacts_for(kind, place_key, number, handle):
    phone = PHONES[place_key].format(n=number % 10000)
    site = f"https://example.com/{handle}"
    telegram = {"type": "telegram", "text": f"@{handle}", "comment": "лучше писать"}
    phone_row = {"type": "phone", "text": phone, "comment": "днём"}
    if kind == "coupon":
        rows = [
            {"type": "website", "text": site, "comment": "промокод в объявлении"},
            telegram,
        ]
    elif kind == "job":
        rows = [telegram]
    elif kind == "market":
        rows = [telegram, phone_row]
    elif kind == "online":
        rows = [{"type": "website", "text": site, "comment": ""}, telegram]
    elif kind == "social":
        rows = [telegram]
    else:
        rows = [phone_row, telegram]
        if number % 2 == 0:
            rows.append({"type": "whatsapp", "text": phone, "comment": ""})
    if number % 7 == 0:
        rows.append({"type": "custom", "text": "у входа скажите, что из Клуба", "comment": ""})
    return rows


def location_for(kind, scope, city_id, number):
    if scope == "world":
        if kind in {"job", "online"}:
            return "Удалённо, город не важен"
        if kind == "coupon":
            return ""
        if kind == "market":
            return "Отправлю почтой"
        return "Онлайн, ссылку пришлю"
    if scope == "country":
        if kind == "place":
            return "По всей стране, напишите свой город"
        if kind == "market":
            return "Могу отправить по стране"
        if kind == "job":
            return "Офис есть, город обсудим"
        return ""
    street = ADDRESSES[city_id].format(n=10 + (number % 80))
    if kind in {"job", "online"}:
        return ""
    if kind == "coupon" and number % 2:
        return ""
    if number % 3 == 0:
        return f"{street}. [Карта]({MAPS[city_id]})"
    return street


def promo_for(kind, number):
    if kind != "coupon":
        return ""
    return f"CLUB{number % 90 + 10}"


def build():
    assert len(CATALOG) == 76, len(CATALOG)
    now = timezone.now().replace(microsecond=0)
    users = []
    for index, (slug, name, city, country, bio) in enumerate(USERS):
        users.append({
            "id": str(uuid.uuid4()),
            "slug": slug,
            "email": f"{slug}@seed.test",
            "full_name": name,
            "city": city,
            "country": country,
            "bio": bio,
            "created_at": now - timedelta(days=120 - index),
        })

    parents = {
        category.id: category.parent_id
        for category in Category.objects.exclude(parent=None)
    }
    items = []
    for sub_index, (subcategory, _category, kind, titles) in enumerate(CATALOG):
        parent_id = parents.get(subcategory)
        if not parent_id:
            continue
        for slot, title in enumerate(titles):
            number = sub_index * 4 + slot
            if slot == 3 and sub_index % 3 == 0:
                scope, country_id, city_id = "world", None, None
            elif slot == 3:
                scope, country_id, city_id = "country", COUNTRIES[sub_index % 3], None
            else:
                scope = "city"
                country_id, city_id = CITIES[(sub_index * 3 + slot) % len(CITIES)]
            author = users[number % len(users)]
            published = now - timedelta(days=number % 70, hours=number % 18)
            updated = published + timedelta(days=4) if number % 4 == 0 else published
            expires = {
                0: None,
                1: now + timedelta(days=7),
                2: now + timedelta(days=30),
                3: now + timedelta(days=90),
                4: now + timedelta(days=365),
            }[number % 5]
            place_key = city_id or country_id
            handle = f"{author['slug'].replace('-', '')}{number % 100:02d}"[:32]
            closing = CLOSINGS[kind][slot]
            items.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "description": f"{title}. {closing}",
                "category_id": parent_id,
                "subcategory_id": subcategory,
                "country_id": country_id,
                "city_id": city_id,
                "author_id": author["id"],
                "published_at": published,
                "created_at": published,
                "updated_at": updated,
                "expires_at": expires,
                "location": location_for(kind, scope, city_id, number),
                "contacts": contacts_for(kind, place_key, number, handle),
                "promo_code": promo_for(kind, number),
            })

    commented = [item for index, item in enumerate(items) if index % 3 == 1][:100]
    comments = []
    for index, item in enumerate(commented):
        author = users[(index + 3) % len(users)]
        if author["id"] == item["author_id"]:
            author = users[(index + 4) % len(users)]
        parent_id = str(uuid.uuid4())
        parent_at = item["published_at"] + timedelta(days=1 + index % 5, hours=index % 8)
        comments.append({
            "id": parent_id,
            "item_id": item["id"],
            "author_id": author["id"],
            "reply_to_id": None,
            "text": COMMENTS[index % len(COMMENTS)],
            "vibe": ("good", "good", "neutral", "good", "bad")[index % 5],
            "created_at": parent_at,
        })
        for reply_index in range(2):
            reply_author = users[(index + 5 + reply_index) % len(users)]
            comments.append({
                "id": str(uuid.uuid4()),
                "item_id": item["id"],
                "author_id": reply_author["id"],
                "reply_to_id": parent_id,
                "text": REPLIES[(index + reply_index) % len(REPLIES)],
                "vibe": None,
                "created_at": parent_at + timedelta(hours=3 + reply_index * 5),
            })

    votes = []
    for index, item in enumerate(items):
        if index % 3:
            continue
        for shift in (1, 4):
            voter = users[(index + shift) % len(users)]
            if voter["id"] == item["author_id"]:
                continue
            votes.append({
                "id": str(uuid.uuid4()),
                "user_id": voter["id"],
                "item_id": item["id"],
                "created_at": item["published_at"] + timedelta(days=2),
            })

    return users, items, comments, votes


def insert_users(users):
    values = []
    for user in users:
        values.append("(" + ", ".join([
            sql_quote(user["id"]) + "::uuid",
            sql_quote("!"),
            sql_quote(user["slug"]),
            sql_quote(user["email"]),
            sql_quote(user["full_name"]),
            sql_quote(user["bio"]),
            sql_quote(user["city"]),
            sql_quote(user["country"]),
            "0",
            "0",
            "0",
            "0",
            sql_quote(user["created_at"]),
            sql_quote(user["created_at"]),
            "'{}'::jsonb",
            "'{}'::varchar[]",
            "false",
            "false",
        ]) + ")")
    return f"""
INSERT INTO users (
    id, password, slug, email, full_name, bio, city, country,
    rating, upvotes, items_count, comments_count,
    created_at, updated_at, metadata, roles, is_staff, is_superuser
) VALUES
{','.join(values)};
"""


def insert_items(items):
    values = []
    for item in items:
        values.append("(" + ", ".join([
            sql_quote(item["id"]) + "::uuid",
            sql_quote(item["title"]),
            sql_quote(item["description"]),
            sql_quote(item["category_id"]),
            sql_quote(item["subcategory_id"]),
            sql_quote(item["country_id"]),
            sql_quote(item["city_id"]),
            sql_quote(item["author_id"]) + "::uuid",
            "'visible'",
            "0",
            "0",
            "0",
            sql_quote(item["published_at"]),
            sql_quote(item["expires_at"]),
            sql_quote(item["created_at"]),
            sql_quote(item["updated_at"]),
            sql_quote(item["location"]),
            sql_quote(item["contacts"]) + "::jsonb",
            sql_quote(item["promo_code"]),
            "'[]'::jsonb",
            "0",
            "0",
        ]) + ")")
    return f"""
INSERT INTO items (
    id, title, description, category_id, subcategory_id, country_id, city_id, author_id,
    visibility, upvotes, rating, comment_count, published_at, expires_at, created_at, updated_at,
    location, contacts, promo_code, images, bookmark_count, view_count
) VALUES
{','.join(values)};
"""


def insert_comments(comments):
    values = []
    for comment in comments:
        values.append("(" + ", ".join([
            sql_quote(comment["id"]) + "::uuid",
            sql_quote(comment["author_id"]) + "::uuid",
            sql_quote(comment["item_id"]) + "::uuid",
            sql_quote(comment["reply_to_id"]) + ("::uuid" if comment["reply_to_id"] else ""),
            sql_quote(comment["text"]),
            sql_quote(comment["vibe"]),
            "0",
            "0",
            sql_quote(comment["created_at"]),
            sql_quote(comment["created_at"]),
        ]) + ")")
    return f"""
INSERT INTO comments (
    id, author_id, item_id, reply_to_id, text, vibe, upvotes, rating, created_at, updated_at
) VALUES
{','.join(values)};
"""


def insert_votes(votes):
    if not votes:
        return ""
    values = []
    for vote in votes:
        values.append("(" + ", ".join([
            sql_quote(vote["id"]) + "::uuid",
            sql_quote(vote["user_id"]) + "::uuid",
            sql_quote(vote["item_id"]) + "::uuid",
            sql_quote(vote["created_at"]),
        ]) + ")")
    return f"""
INSERT INTO item_votes (id, user_id, item_id, created_at) VALUES
{','.join(values)};
"""


RECOUNT = r"""
UPDATE items SET upvotes = 0, rating = 0, comment_count = 0 WHERE deleted_at IS NULL;
UPDATE comments SET rating = 0 WHERE deleted_at IS NULL;
UPDATE users SET upvotes = 0, rating = 0, items_count = 0, comments_count = 0 WHERE deleted_at IS NULL;
UPDATE geo_countries SET items_count = 0;
UPDATE geo_cities SET items_count = 0;

UPDATE items i
SET upvotes = v.n
FROM (
    SELECT item_id, count(*)::int AS n
    FROM item_votes
    GROUP BY item_id
) v
WHERE i.id = v.item_id AND i.deleted_at IS NULL;

UPDATE users u
SET upvotes = src.n
FROM (
    SELECT i.author_id, count(*)::int AS n
    FROM item_votes v
    JOIN items i ON i.id = v.item_id
    WHERE i.deleted_at IS NULL
    GROUP BY i.author_id
) src
WHERE u.id = src.author_id;

UPDATE items i
SET rating = i.upvotes + coalesce(src.points, 0)
FROM (
    SELECT c.item_id,
           sum(CASE c.vibe WHEN 'good' THEN 5 WHEN 'bad' THEN -5 ELSE 0 END)::int AS points
    FROM comments c
    JOIN items it ON it.id = c.item_id
    WHERE c.deleted_at IS NULL
      AND c.reply_to_id IS NULL
      AND c.author_id IS DISTINCT FROM it.author_id
    GROUP BY c.item_id
) src
WHERE i.id = src.item_id;

UPDATE users u
SET rating = u.upvotes + coalesce(src.points, 0)
FROM (
    SELECT c.author_id,
           sum(CASE c.vibe WHEN 'good' THEN 5 WHEN 'bad' THEN -5 ELSE 0 END)::int AS points
    FROM comments c
    JOIN items it ON it.id = c.item_id
    WHERE c.deleted_at IS NULL
      AND c.reply_to_id IS NULL
      AND c.author_id IS DISTINCT FROM it.author_id
    GROUP BY c.author_id
) src
WHERE u.id = src.author_id;

UPDATE items i
SET comment_count = src.n
FROM (
    SELECT item_id, count(*)::int AS n
    FROM comments
    WHERE deleted_at IS NULL AND reply_to_id IS NULL
    GROUP BY item_id
) src
WHERE i.id = src.item_id;

UPDATE users u
SET items_count = src.n
FROM (
    SELECT author_id, count(*)::int AS n
    FROM items
    WHERE deleted_at IS NULL
      AND visibility = 'visible'
      AND (expires_at IS NULL OR expires_at > now())
    GROUP BY author_id
) src
WHERE u.id = src.author_id;

UPDATE users u
SET comments_count = src.n
FROM (
    SELECT author_id, count(*)::int AS n
    FROM comments
    WHERE deleted_at IS NULL AND author_id IS NOT NULL
    GROUP BY author_id
) src
WHERE u.id = src.author_id;

UPDATE geo_countries c
SET items_count = src.n
FROM (
    SELECT c2.id, count(i.id)::int AS n
    FROM geo_countries c2
    LEFT JOIN items i
      ON i.deleted_at IS NULL
     AND i.visibility = 'visible'
     AND (i.expires_at IS NULL OR i.expires_at > now())
     AND i.country_id = c2.id
    GROUP BY c2.id
) src
WHERE c.id = src.id;

UPDATE geo_cities city
SET items_count = src.n
FROM (
    SELECT g.id, count(i.id)::int AS n
    FROM geo_cities g
    LEFT JOIN items i
      ON i.deleted_at IS NULL
     AND i.visibility = 'visible'
     AND (i.expires_at IS NULL OR i.expires_at > now())
     AND (
        i.city_id = g.id
        OR (i.city_id IS NULL AND i.country_id = g.country_id)
     )
    GROUP BY g.id
) src
WHERE city.id = src.id;
"""

CLEANUP = """
DELETE FROM item_votes
WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@seed.test')
   OR item_id IN (
        SELECT id FROM items WHERE author_id IN (SELECT id FROM users WHERE email LIKE '%@seed.test')
   );
DELETE FROM comments
WHERE author_id IN (SELECT id FROM users WHERE email LIKE '%@seed.test')
   OR item_id IN (
        SELECT id FROM items WHERE author_id IN (SELECT id FROM users WHERE email LIKE '%@seed.test')
   );
DELETE FROM items WHERE author_id IN (SELECT id FROM users WHERE email LIKE '%@seed.test');
DELETE FROM users WHERE email LIKE '%@seed.test';
"""


def main():
    users, items, comments, votes = build()
    sql = "BEGIN;\n" + CLEANUP + insert_users(users) + insert_items(items) + insert_comments(comments) + insert_votes(votes) + RECOUNT + "COMMIT;\n"
    with connection.cursor() as cursor:
        cursor.execute(sql)
    print(f"users={len(users)} items={len(items)} comments={len(comments)} votes={len(votes)}")


if __name__ == "__main__":
    main()
